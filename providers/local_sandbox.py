# providers/local_sandbox.py
from __future__ import annotations
from typing import List, Tuple
from executor import load_policy, is_allowed
import subprocess
import shlex

class LocalSandbox:
    def __init__(self) -> None:
        self.policy = load_policy()

    def run(self, command: str, args: List[str]) -> Tuple[int, str, str]:
        allow = self.policy.get("allowlist", [])
        timeout = int(self.policy.get("timeout_sec", 30))

        if not is_allowed(command, allow):
            raise PermissionError(f"Command '{command}' not in allowlist: {allow}")

        proc = subprocess.run([command, *args], capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout, proc.stderr

    def close(self) -> None:
        pass
