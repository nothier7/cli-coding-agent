import os
import shlex
import subprocess
import sys
from rich.align import Align
from rich.text import Text
from pathlib import Path
from typing import List

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text


CHERNO_ASCII = r"""
      ___           ___           ___           ___           ___           ___     
     /\  \         /\__\         /\  \         /\  \         /\__\         /\  \    
    /::\  \       /:/  /        /::\  \       /::\  \       /::|  |       /::\  \   
   /:/\:\  \     /:/__/        /:/\:\  \     /:/\:\  \     /:|:|  |      /:/\:\  \  
  /:/  \:\  \   /::\  \ ___   /::\~\:\  \   /::\~\:\  \   /:/|:|  |__   /:/  \:\  \ 
 /:/__/ \:\__\ /:/\:\  /\__\ /:/\:\ \:\__\ /:/\:\ \:\__\ /:/ |:| /\__\ /:/__/ \:\__\
 \:\  \  \/__/ \/__\:\/:/  / \:\~\:\ \/__/ \/_|::\/:/  / \/__|:|/:/  / \:\  \ /:/  /
  \:\  \            \::/  /   \:\ \:\__\      |:|::/  /      |:/:/  /   \:\  /:/  / 
   \:\  \           /:/  /     \:\ \/__/      |:|\/__/       |::/  /     \:\/:/  /  
    \:\__\         /:/  /       \:\__\        |:|  |         /:/  /       \::/  /   
     \/__/         \/__/         \/__/         \|__|         \/__/         \/__/    
"""


console = Console()
HISTORY = Path(".agent/.repl_history")
HISTORY.parent.mkdir(exist_ok=True, parents=True)

HELP = """\
Commands:
  :help              Show this help
  :dry on|off        Toggle dry-run (preview only)
  :debug on|off      Toggle debug raw response printing
  :rollback          Git rollback last commit (no prompt)
  :clear             Clear the screen
  :exit / :quit      Exit REPL
"""

def _bool_toggle(val: str, current: bool) -> bool:
    v = val.strip().lower()
    if v in ("on", "true", "1", "yes", "y"): return True
    if v in ("off", "false", "0", "no", "n"): return False
    return current

def run_engine(prompt: str, dry: bool, debug: bool) -> int:
    argv = [sys.executable, "main.py"]
    if dry:
        argv.append("--dry-run")
    if debug:
        argv.append("--debug")
    argv.append(prompt)
    # Inherit the console so main.py can show prompts and read your input
    return subprocess.call(argv)


def run_rollback() -> int:
    argv = [sys.executable, "main.py", "--rollback"]
    return subprocess.call(argv)

def banner(dry: bool, debug: bool):
    art = Text(CHERNO_ASCII, style="bold cyan")
    info = Text.from_markup(
        f"[dim]dry-run:[/dim] {'[yellow]on[/yellow]' if dry else '[green]off[/green]'}   "
        f"[dim]debug:[/dim] {'[yellow]on[/yellow]' if debug else '[green]off[/green]'}   "
        f"[dim]engine:[/dim] main.py\n"
        f"[dim]Type natural language prompts. Commands start with ':' (e.g., :help)[/dim]"
    )
    console.print(Panel(Align.center(art), border_style="cyan", title="CHERNO • Your Pocket /Coding Agent "))
    console.print(Panel(info, border_style="cyan"))


def main():
    os.environ.setdefault("PYTHONUTF8", "1")  # avoid encoding hiccups on Windows
    dry = False
    debug = False

    session = PromptSession(
        message=[("class:prompt", "cherno> ")],
        history=FileHistory(str(HISTORY)),
        completer=WordCompleter([":help", ":dry on", ":dry off", ":debug on", ":debug off", ":rollback", ":clear", ":exit", ":quit"]),
        style=Style.from_dict({
            "prompt": "bold cyan",
        }),
    )
    console.clear()
    banner(dry, debug)

    while True:
        try:
            inp = session.prompt()
        except (EOFError, KeyboardInterrupt):
            console.print("[dim]bye[/dim]")
            break

        if not inp.strip():
            continue

        if inp.startswith(":"):
            cmd, *rest = inp[1:].split(" ", 1)
            arg = rest[0] if rest else ""
            cmd = cmd.lower()

            if cmd in ("exit", "quit"):
                break
            elif cmd == "help":
                console.print(Panel(HELP, title="Help", border_style="magenta"))
            elif cmd == "dry":
                dry = _bool_toggle(arg, dry)
                console.print(f"[dim]dry-run ->[/dim] {'[yellow]on[/yellow]' if dry else '[green]off[/green]'}")
            elif cmd == "debug":
                debug = _bool_toggle(arg, debug)
                console.print(f"[dim]debug ->[/dim] {'[yellow]on[/yellow]' if debug else '[green]off[/green]'}")
            elif cmd == "rollback":
                code = run_rollback()
                if code == 0:
                    console.print("[green]Rolled back last commit.[/green]")
                else:
                    console.print(f"[red]Rollback failed (exit {code}).[/red]")
            elif cmd == "clear":
                console.clear()
                banner(dry, debug)
            else:
                console.print(f"[yellow]Unknown command:[/yellow] :{cmd}  (try :help)")
            continue

        # normal prompt → run engine
        code = run_engine(inp, dry=dry, debug=debug)
        if code != 0:
            console.print(f"[red]engine exited with code {code}[/red]")

if __name__ == "__main__":
    main()
