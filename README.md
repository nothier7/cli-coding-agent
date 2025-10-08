# Cherno · CLI Coding Agent

Cherno is a command line assistant that turns natural-language requests into concrete edits inside your workspace. It talks to OpenAI's Responses API, plans the changes it should make, shows you the resulting diff, and only writes to disk (and Git) after you confirm.

## Quick Start
- Install Python 3.10+ and create a virtual environment if desired.
- Install dependencies and the CLI in editable mode:
  ```
  pip install -e .
  ```
- Provide credentials. Set `OPENAI_API_KEY` (and optionally `MODEL`) in your shell or in a `.env` file at the project root. `MODEL` defaults to `gpt-5-codex`.
- Launch the interactive REPL:
  ```
  cherno
  ```
- Or run a one-off instruction without the REPL:
  ```
  python main.py "Add unit tests for planner.plan_from_intent"
  ```

## What Happens During a Run
1. **Intent parsing** - Cherno sends the conversation history plus your latest request to the model and validates the structured intent it gets back.
2. **Planning & synthesis** - the intent is expanded into concrete steps (read files, synthesize a patch, show a diff, run a command).
3. **Confirmation & execution** - you preview the diff before approving. Once confirmed, Cherno writes the file, commits the change, and optionally runs planned commands.

If the repository is not already initialized, Cherno runs `git init` and creates an initial commit so subsequent writes can be captured.

## REPL Controls
- `:help` - show all commands.
- `:dry on|off` - toggle dry-run mode (synthesizes changes but skips writes and commits).
- `:debug on|off` - print the raw model response for debugging.
- `:rollback` - revert the most recent commit via `git reset --hard HEAD~1`.
- `:clear` - refresh the terminal banner.
- `:exit` or `:quit` - leave the REPL.

Each natural-language prompt in the REPL invokes the same pipeline as a direct `python main.py` run, with your choices persisted in `.agent/.repl_history`.

## Architecture Overview
- `main.py` orchestrates the run: loads chat memory, builds LLM requests, prints the plan, handles confirmation, and writes files or runs commands.
- `llm.py` loads environment variables (via `python-dotenv`) and constructs the OpenAI client.
- `intents.py` defines the structured intent schema (`edit_file`, `create_file`, `run_command`) and validates payloads returned by the model.
- `planner.py` converts an intent into a sequence of step dictionaries the CLI executes.
- `patcher.py` sends instructions plus the original file to the model and returns the synthesized full file content.
- `fs_ops.py` performs safe file reads/writes and builds unified diffs for previews.
- `memory.py` persists the ongoing conversation in `.agent/session.json` so follow-up prompts retain context.
- `sandbox.py` picks a sandbox provider; local execution is default, with an E2B integration available.
- `providers/local_sandbox.py` runs allowlisted commands locally under a configurable timeout.
- `providers/e2b_sandbox.py` connects to the E2B cloud sandbox (requires `E2B_API_KEY`).
- `executor.py` enforces the allowlist defined in `.agent/policy.json` before running commands.
- `git_ops.py` handles repository bootstrapping, add/commit flows, and rollbacks.
- `src/cherno/cli.py` implements the REPL experience, ASCII banner, and command toggles.

Supporting files under `.agent/` hold runtime configuration:
- `policy.json` - command allowlist and timeout. Created on first run; edit it to authorize additional binaries.
- `sandbox.json` - selects the sandbox provider (`local` or `e2b`). Bootstrapped automatically when missing.
- `.repl_history` - prompt history for the REPL.

## Usage Patterns
- **Create files** - "Create `.github/workflows/tests.yml` that runs pytest on push." The plan shows the file before writing.
- **Edit files** - "Update `planner.py` so `show_diff` comes before `write_file`." Cherno reads the file, synthesizes a replacement, and asks you to confirm the diff.
- **Run commands** - "Run tests with pytest." Commands must be allowlisted; otherwise Cherno explains the restriction.
- **Iterate** - Conversational memory means you can give short follow-ups. Delete `.agent/session.json` to restart from a clean slate.
- **Stay dry** - Toggle dry-run in the REPL to preview diffs without touching disk or Git.

Approved changes are written to disk and committed with messages such as `feat(agent): update <path>`. You can amend afterwards if you need custom commit text.

## Extending Cherno
- Add new intent types by updating `intents.py` and `planner.py`.
- Adjust the sandbox policy by editing `.agent/policy.json` (allowlist or timeout).
- Introduce new sandbox providers under `providers/` and switch via `.agent/sandbox.json`.
- Customize synthesis strategies by modifying `patcher.py` or adding new helper modules.
- Package new REPL commands within `src/cherno/cli.py`.

## Troubleshooting
- **Missing dependencies** - install the project with `pip install -e .`. If you prefer pinned versions, add a `requirements.txt` or use a lockfile.
- **Command blocked** - add the binary to the `allowlist` in `.agent/policy.json` and rerun.
- **E2B provider errors** - ensure `E2B_API_KEY` is set and the `e2b` (or `e2b_code_interpreter`) package is installed.
- **Stale memory** - delete `.agent/session.json` to forget previous conversations. Remove `.agent/.repl_history` to clear REPL history.
- **Unexpected Git state** - use `:rollback` in the REPL or run `python main.py --rollback` to revert the latest commit.

With these pieces in place, you control every change Cherno proposes while steering it entirely through natural language.
