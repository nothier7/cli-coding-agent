# executor.py
import json
import shlex
import subprocess
from pathlib import Path
from typing import List, Tuple

from command_safety import analyze_command

POLICY_PATH = Path(".agent/policy.json")

DEFAULT_POLICY = {
    "allowlist": ["python", "pytest", "pip", "node", "npm", "pnpm", "uv", "ruff", "black", "bash"],
    "timeout_sec": 30
}

def load_policy() -> dict:
    if POLICY_PATH.exists():
        try:
            return json.loads(POLICY_PATH.read_text())
        except Exception:
            pass
    POLICY_PATH.parent.mkdir(exist_ok=True)
    POLICY_PATH.write_text(json.dumps(DEFAULT_POLICY, indent=2))
    return DEFAULT_POLICY

def is_allowed(cmd: str, allowlist: List[str]) -> bool:
    # compare the binary (first token)
    first = shlex.split(cmd)[0] if cmd.strip() else ""
    base = Path(first).name
    return base in {Path(x).name for x in allowlist}


def ensure_safe_arguments(command: str, args: List[str]) -> None:
    unsafe_tokens = ["&&", "||", ";", "|", "`", "$(", "${"]
    for arg in args:
        if not isinstance(arg, str):
            raise ValueError("Command arguments must be strings.")
        if any(token in arg for token in unsafe_tokens):
            raise PermissionError(f"Argument '{arg}' contains unsupported shell control tokens.")
        if any(ord(ch) < 32 for ch in arg):
            raise PermissionError("Control characters detected in command arguments.")

    analysis = analyze_command(command, args)
    if analysis.risk == "block":
        reasons = "; ".join(analysis.reasons) or "Command blocked by safety policy."
        raise PermissionError(reasons)

def run_command(command: str, args: List[str]) -> Tuple[int, str, str]:
    policy = load_policy()
    allow = policy.get("allowlist", [])
    timeout = int(policy.get("timeout_sec", 30))

    if not is_allowed(command, allow):
        raise PermissionError(f"Command '{command}' not in allowlist: {allow}")

    ensure_safe_arguments(command, args)

    proc = subprocess.run([command, *args], capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr
