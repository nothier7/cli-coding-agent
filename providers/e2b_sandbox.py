# providers/e2b_sandbox.py
from __future__ import annotations
from typing import List, Tuple, Optional
import os

class E2BSandbox:
    """
    Minimal E2B provider:
    - starts a sandbox
    - runs foreground commands via sandbox.commands.run()
    - returns (exit_code, stdout, stderr)
    - shuts down on close()
    """
    def __init__(self, template: Optional[str] = None, cwd: Optional[str] = None, envs: Optional[dict] = None) -> None:
        try:
            # Primary SDK (per docs)
            from e2b import Sandbox  # type: ignore
            self._pkg = "e2b"
        except Exception:
            # Some installs use e2b_code_interpreter
            from e2b_code_interpreter import Sandbox  # type: ignore
            self._pkg = "e2b_code_interpreter"

        api_key = os.getenv("E2B_API_KEY")
        if not api_key:
            raise RuntimeError("E2B_API_KEY not set. Export it in your environment or .env.")

        # Create sandbox (timeout seconds defaults to 300)
        # Docs show Sandbox() constructor with optional template/timeout/envs. :contentReference[oaicite:1]{index=1}
        self._sbx = Sandbox(template=template, envs=envs)

        # Track CWD inside sandbox; you can mkdir -p it later if needed.
        self._cwd = cwd

    def run(self, command: str, args: List[str]) -> Tuple[int, str, str]:
        cmd = " ".join([command, *[self._shell_quote(a) for a in args]]).strip()

        # Foreground run (returns CommandResult). Python API has commands.run with timeout/cwd/envs. :contentReference[oaicite:2]{index=2}
        result = self._sbx.commands.run(
            cmd=cmd,
            cwd=self._cwd,
            # don’t pass temperature anywhere; we respect your note to avoid it
        )

        # Result fields vary slightly across SDK versions — extract defensively
        code = (
            getattr(result, "exit_code", None) or
            getattr(result, "code", None) or
            0
        )
        out = (
            getattr(result, "stdout", None) or
            getattr(result, "output", None) or
            ""
        )
        err = getattr(result, "stderr", None) or ""

        # Some SDKs expose bytes; normalize to str
        if isinstance(out, (bytes, bytearray)):
            out = out.decode("utf-8", errors="replace")
        if isinstance(err, (bytes, bytearray)):
            err = err.decode("utf-8", errors="replace")

        return int(code), str(out), str(err)

    def close(self) -> None:
        try:
            if getattr(self, "_sbx", None):
                self._sbx.kill()
        except Exception:
            # If it's already dead or kill isn't available, ignore
            pass

    @staticmethod
    def _shell_quote(s: str) -> str:
        # conservative shell quoting
        if not s:
            return "''"
        if all(c.isalnum() or c in "._-/:=" for c in s):
            return s
        return "'" + s.replace("'", "'\"'\"'") + "'"
