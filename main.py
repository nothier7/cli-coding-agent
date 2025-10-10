# main.py
import sys
import json
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple
from sandbox import make_sandbox
from llm import client, MODEL
from intents import TOOL_DEFS, parse_intent
from memory import load_memory, save_memory
from planner import plan_from_intent
from fs_ops import read_file_text, write_file_text, compute_unified_diff
from patcher import synthesize_new_contents
from git_ops import ensure_repo, commit_paths, rollback_last
from rich.console import Console
from rich.json import JSON as RichJSON
from command_safety import analyze_command, dry_run_required

SYSTEM_PROMPT = (
    "You are a coding agent that ONLY returns a single structured intent "
    "by calling the tool function emit_intent. Do not explain. "
    "Infer file paths when reasonable. If multiple steps are needed, choose the first, "
    "most atomic intent to begin progress."
)


console = Console()


def print_rule(title: str) -> None:
    bar = "=" * 10
    print(f"\n{bar} {title} {bar}")


def print_panel(text: str, title: str) -> None:
    print(f"[{title}]")
    print(text)
    print()


def print_json(obj: Dict[str, Any]) -> None:
    print(json.dumps(obj, indent=2))


@contextmanager
def print_status(message: str):
    print(message)
    try:
        yield
    finally:
        print("Finished.")


def wrap_text(role: str, text: str) -> Dict[str, Any]:
    content_type = "output_text" if role == "assistant" else "input_text"
    return {"role": role, "content": [{"type": content_type, "text": text}]}


def build_response_messages(system_prompt: str, turns: List[Dict[str, str]], user_prompt: str) -> List[Dict[str, Any]]:
    msgs: List[Dict[str, Any]] = [wrap_text("system", system_prompt)]
    for turn in turns:
        msgs.append(wrap_text(turn["role"], turn["content"]))
    msgs.append(wrap_text("user", user_prompt))
    return msgs


def truncate_text(text: str, limit: int = 500) -> str:
    if len(text) <= limit:
        return text
    remaining = len(text) - limit
    return f"{text[:limit]}... ({remaining} more chars)"


def build_assistant_summary(intent: Any, plan: List[Dict[str, Any]], actions: List[Dict[str, Any]]) -> str:
    payload = {
        "intent": intent.model_dump(),
        "plan": plan,
        "actions": actions,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def extract_tool_result(resp: Any) -> Dict[str, Any]:
    """
    Robustly extract the tool_result payload from Responses API output.
    """
    output = getattr(resp, "output", None)
    if not output:
        raise ValueError("No output in response")

    def get_attr(item: Any, key: str, default: Any = None) -> Any:
        if isinstance(item, dict):
            return item.get(key, default)
        return getattr(item, key, default)

    # Check for direct function_call/tool_result entries.
    for item in output:
        item_type = get_attr(item, "type")
        name = get_attr(item, "name")

        if item_type == "function_call" and name == "emit_intent":
            args = get_attr(item, "arguments")
            if isinstance(args, str):
                try:
                    payload = json.loads(args)
                except json.JSONDecodeError as exc:
                    raise ValueError("Function call arguments are not valid JSON") from exc
            elif isinstance(args, dict):
                payload = args
            else:
                raise ValueError("Function call arguments missing or invalid")
            return payload

        if item_type == "tool_result" and name == "emit_intent":
            payload = get_attr(item, "output")
            if not isinstance(payload, dict):
                raise ValueError("Tool result 'output' is not an object")
            return payload

    # Fall back to older SDK shape with embedded content fragments.
    for item in output:
        content = get_attr(item, "content") or []
        for frag in content:
            frag_type = get_attr(frag, "type")
            if frag_type == "tool_result" and get_attr(frag, "tool_name") == "emit_intent":
                payload = get_attr(frag, "output")
                if not isinstance(payload, dict):
                    raise ValueError("Tool result 'output' is not an object")
                return payload

    raise ValueError("No tool output for emit_intent found in response")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <your natural language request>")
        sys.exit(1)

    user_prompt = " ".join(sys.argv[1:])
    turns = load_memory()

    print_rule("Intent Parsing (Step 1)")
    print_panel(user_prompt, "Your Prompt")

    # Build messages (system + prior user/assistant turns + new user prompt)
    response_msgs = build_response_messages(SYSTEM_PROMPT, turns, user_prompt)

    with print_status("Asking Codex to produce a structured intent..."):
        resp = client.responses.create(
            model=MODEL,
            input=response_msgs,
            tools=TOOL_DEFS,
            tool_choice={"type": "function", "name": "emit_intent"},
        )

    try:
        payload = extract_tool_result(resp)
        intent_obj = payload.get("intent")
        if intent_obj is None:
            raise ValueError("emit_intent returned no 'intent' field")
        intent = parse_intent(intent_obj)
    except Exception as e:
        print("Failed to parse intent")
        print(str(e))
        # For debugging, print raw response compactly:
        try:
            raw = resp.to_dict() if hasattr(resp, "to_dict") else resp
            print(json.dumps(raw, indent=2)[:4000])
        except Exception:
            pass
        sys.exit(2)

    print_rule("Parsed Intent")
    print_json(intent.model_dump())

    print("\nStep 1 complete: parsed intent printed above (no execution performed).")

    # --- Step 3: Plan + Patch Synthesis + Git + Executor ---
    intent_dict = intent.model_dump()
    plan = plan_from_intent(intent_dict)

    console.rule("[bold cyan]Plan[/bold cyan]")
    console.print(RichJSON(json.dumps(plan, indent=2)))
    sandbox = make_sandbox()

    ensure_repo(".")  # init git if needed

    confirm_needed = False
    pending_write: Optional[Tuple[str, str]] = None  # (path, contents)
    synthesized_cache = {}  # path -> synthesized new contents (for show_diff/write_file)
    session_actions: List[Dict[str, Any]] = []

    for step in plan:
        kind = step["kind"]

        if kind == "read_file":
            ok, text, err = read_file_text(step["path"])
            if not ok:
                console.print(f"[red][read_file][/red] {err}")
            else:
                console.print(f"[green][read_file][/green] {step['path']} ({len(text)} bytes)")
                synthesized_cache[step["path"] + "::old"] = text

        elif kind == "synthesize_patch":
            path = step["path"]
            instructions = step.get("instructions", "")
            original = synthesized_cache.get(path + "::old", "")
            console.print(f"[yellow]Synthesizing patch for {path}...[/yellow]")
            new_text, validation_issues = synthesize_new_contents(path, original, instructions)
            if not new_text:
                console.print(f"[red]Failed to synthesize new contents for {path}[/red]")
                continue
            synthesized_cache[path + "::new"] = new_text
            if validation_issues:
                synthesized_cache[path + "::issues"] = validation_issues
                console.print("[yellow]Validation warnings:[/yellow]")
                for issue in validation_issues:
                    console.print(f" - {issue}")

        elif kind == "show_diff":
            path = step["path"]
            proposed = step.get("contents")
            if proposed is None:
                proposed = synthesized_cache.get(path + "::new")

            if proposed is None:
                console.print(f"[red][show_diff][/red] No proposed contents for {path}")
                continue

            ok, old, err = read_file_text(path)
            old = old if ok else ""
            diff = compute_unified_diff(old, proposed, path)
            title = f"Unified diff for {path}" if old else f"New file preview: {path}"
            console.rule(f"[bold magenta]{title}[/bold magenta]")
            console.print(diff or "(no changes)")
            issues = synthesized_cache.get(path + "::issues", [])
            if issues:
                console.print("[yellow]Validation warnings (write requires explicit override):[/yellow]")
                for issue in issues:
                    console.print(f" - {issue}")
            confirm_needed = True
            pending_write = (path, proposed)

        elif kind == "write_file":
            # gated below by confirmation
            pass

        elif kind == "run_command":
            cmd = step["command"]
            args = step.get("args", [])
            console.rule("[bold cyan]Planned Command[/bold cyan]")
            console.print(f"{cmd} {' '.join(args)}")
            analysis = analyze_command(cmd, args)
            if analysis.reasons:
                console.print("[yellow]Command safety review:[/yellow]")
                for reason in analysis.reasons:
                    console.print(f" - {reason}")

            command_entry: Dict[str, Any] = {
                "type": "run_command",
                "command": cmd,
                "args": args,
                "risk": analysis.risk,
                "reasons": analysis.reasons,
            }
            if analysis.risk == "block":
                console.print("[red]Command contains disallowed shell control operators and was blocked.[/red]")
                command_entry["decision"] = "blocked"
                session_actions.append(command_entry)
                continue

            if analysis.risk == "caution" and dry_run_required(analysis):
                console.print("[yellow]Dry-run enforced by AGENT_HIGH_RISK_DRY_RUN; command execution skipped.[/yellow]")
                command_entry["decision"] = "dry-run"
                session_actions.append(command_entry)
                continue

            if analysis.risk == "caution":
                choice = input("\nHigh-risk command detected. Type 'run' to execute, 'dry' for a dry-run skip, or anything else to cancel: ").strip().lower()
                if choice == "dry":
                    console.print("Dry-run requested; command was not executed.")
                    command_entry["decision"] = "dry-run"
                    session_actions.append(command_entry)
                    continue
                if choice != "run":
                    console.print("Skipped.")
                    command_entry["decision"] = "skipped"
                    session_actions.append(command_entry)
                    continue
                execute = True
            else:
                ans = input("\nRun this command now? [y/N]: ").strip().lower()
                if ans != "y":
                    console.print("Skipped.")
                    command_entry["decision"] = "skipped"
                    session_actions.append(command_entry)
                    continue
                execute = True

            if execute:
                try:
                    code, out, err = sandbox.run(cmd, args)
                    console.rule("[bold green]stdout[/bold green]"); print(out or "(empty)")
                    console.rule("[bold red]stderr[/bold red]"); print(err or "(empty)")
                    console.print(f"\nExit code: {code}")
                    command_entry.update(
                        exit_code=code,
                        stdout=truncate_text(out or "", 500),
                        stderr=truncate_text(err or "", 500),
                        decision="executed",
                    )
                except Exception as ex:
                    console.print(f"[red]Command failed: {ex}[/red]")
                    command_entry["decision"] = "error"
                    command_entry["error"] = str(ex)
            else:
                console.print("Skipped.")
            session_actions.append(command_entry)

        elif kind == "error":
            message = step.get("message", "Planning error.")
            console.print(f"[red][plan][/red] {message}")
            session_actions.append(
                {
                    "type": "plan_error",
                    "message": message,
                    "path": step.get("path"),
                }
            )
            break

        else:
            console.print(f"[yellow]Unknown step kind: {kind}[/yellow]")

    # Confirmation + write + commit
    write_entry: Optional[Dict[str, Any]] = None
    if confirm_needed and pending_write:
        path, contents = pending_write
        issues = synthesized_cache.get(path + "::issues", [])
        if issues:
            console.print("[yellow]Validation warnings detected for this file:[/yellow]")
            for issue in issues:
                console.print(f" - {issue}")
            ans = input("\nType 'force' to write despite validation issues, or anything else to cancel: ").strip().lower()
            if ans != "force":
                console.print("Aborted due to validation issues (no files changed).")
                write_entry = {"type": "write_file", "path": path, "applied": False, "reason": "validation_failed"}
            else:
                console.print("[yellow]Proceeding despite validation warnings.[/yellow]")
                ok, err = write_file_text(path, contents)
                if ok:
                    console.print(f"[green][write_file][/green] Wrote {path}")
                    write_entry = {"type": "write_file", "path": path, "applied": True, "override_validation": True}
                    try:
                        commit_paths([path], f"feat(agent): update {path}")
                        console.print("[green]Committed to git[/green]")
                        write_entry["committed"] = True
                    except Exception as ex:
                        console.print(f"[yellow]Write succeeded but commit failed: {ex}[/yellow]")
                        write_entry["committed"] = False
                        write_entry["commit_error"] = str(ex)
                else:
                    console.print(f"[red][write_file][/red] {err}")
                    write_entry = {"type": "write_file", "path": path, "applied": False, "error": err}
            if write_entry:
                write_entry["validation_issues"] = issues
        else:
            ans = input("\nApply the file change(s)? [y/N]: ").strip().lower()
            if ans == "y":
                ok, err = write_file_text(path, contents)
                if ok:
                    console.print(f"[green][write_file][/green] Wrote {path}")
                    write_entry = {"type": "write_file", "path": path, "applied": True}
                    try:
                        commit_paths([path], f"feat(agent): update {path}")
                        console.print("[green]Committed to git[/green]")
                        write_entry["committed"] = True
                    except Exception as ex:
                        console.print(f"[yellow]Write succeeded but commit failed: {ex}[/yellow]")
                        write_entry["committed"] = False
                        write_entry["commit_error"] = str(ex)
                else:
                    console.print(f"[red][write_file][/red] {err}")
                    write_entry = {"type": "write_file", "path": path, "applied": False, "error": err}
            else:
                console.print("Aborted (no files changed).")
                write_entry = {"type": "write_file", "path": path, "applied": False, "reason": "user_declined"}

    if write_entry:
        session_actions.append(write_entry)

    try:
        sandbox.close()
    except Exception:
        pass

    console.print("\n[dim]Step 3 complete: synthesis if needed, diff preview, git commit, and safe command run.[/dim]")

    turns.append({"role": "user", "content": user_prompt})
    assistant_summary = build_assistant_summary(intent, plan, session_actions)
    turns.append({"role": "assistant", "content": assistant_summary})
    save_memory(turns)


if __name__ == "__main__":
    main()
