# executor.py
import json
import shlex
import subprocess
from pathlib import Path
from typing import List, Tuple

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

def run_command(command: str, args: List[str]) -> Tuple[int, str, str]:
    policy = load_policy()
    allow = policy.get("allowlist", [])
    timeout = int(policy.get("timeout_sec", 30))

    if not is_allowed(command, allow):
        raise PermissionError(f"Command '{command}' not in allowlist: {allow}")

    proc = subprocess.run([command, *args], capture_output=True, text=True, timeout=timeout)
    return proc.returncode, proc.stdout, proc.stderr
