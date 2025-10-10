# providers/e2b_sandbox.py
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

from command_safety import analyze_command, dry_run_required


class E2BSandbox:
    """
    E2B sandbox provider with basic resource limits and safety checks.
    """

    def __init__(self, template: Optional[str] = None, cwd: Optional[str] = None, envs: Optional[dict] = None) -> None:
        try:
            from e2b import Sandbox  # type: ignore
            self._pkg = "e2b"
        except Exception:
            from e2b_code_interpreter import Sandbox  # type: ignore
            self._pkg = "e2b_code_interpreter"

        api_key = os.getenv("E2B_API_KEY")
        if not api_key:
            raise RuntimeError("E2B_API_KEY not set. Export it in your environment or .env.")

        self._cpu_limit = int(os.getenv("E2B_CPU_LIMIT", "2"))
        self._memory_limit_mb = int(os.getenv("E2B_MEMORY_LIMIT_MB", "2048"))
        self._timeout_sec = int(os.getenv("E2B_COMMAND_TIMEOUT", "120"))
        self._max_output_bytes = int(os.getenv("E2B_MAX_OUTPUT_BYTES", str(1_048_576)))

        try:
            self._sbx = Sandbox(template=template, envs=envs, timeout=self._timeout_sec)
        except TypeError:
            # Older SDKs may not support the timeout kwarg.
            self._sbx = Sandbox(template=template, envs=envs)
        self._apply_resource_limits()
        self._cwd = cwd

    def run(self, command: str, args: List[str]) -> Tuple[int, str, str]:
        analysis = analyze_command(command, args)
        if analysis.risk == "block":
            reasons = "; ".join(analysis.reasons) or "Command blocked by sandbox safety policy."
            raise PermissionError(reasons)
        if dry_run_required(analysis):
            raise PermissionError("High-risk command blocked by AGENT_HIGH_RISK_DRY_RUN policy.")

        cmd = " ".join([command, *[self._shell_quote(a) for a in args]]).strip()

        run_kwargs: Dict[str, Any] = {"cmd": cmd, "cwd": self._cwd}
        if self._timeout_sec:
            run_kwargs["timeout"] = self._timeout_sec
        try:
            result = self._sbx.commands.run(**run_kwargs)
        except TypeError:
            run_kwargs.pop("timeout", None)
            result = self._sbx.commands.run(**run_kwargs)

        code = (
            getattr(result, "exit_code", None)
            or getattr(result, "code", None)
            or 0
        )
        out = (
            getattr(result, "stdout", None)
            or getattr(result, "output", None)
            or ""
        )
        err = getattr(result, "stderr", None) or ""

        if isinstance(out, (bytes, bytearray)):
            out = out.decode("utf-8", errors="replace")
        if isinstance(err, (bytes, bytearray)):
            err = err.decode("utf-8", errors="replace")

        out = self._truncate_output(str(out))
        err = self._truncate_output(str(err))

        return int(code), out, err

    def close(self) -> None:
        try:
            if getattr(self, "_sbx", None):
                self._sbx.kill()
        except Exception:
            pass

    @staticmethod
    def _shell_quote(value: str) -> str:
        if not value:
            return "''"
        if all(c.isalnum() or c in "._-/:=" for c in value):
            return value
        return "'" + value.replace("'", "'\"'\"'") + "'"

    def _apply_resource_limits(self) -> None:
        sandbox = getattr(self, "_sbx", None)
        if sandbox is None:
            return

        candidates = ["set_resource_limits", "set_limits", "configure_limits"]
        payloads = [
            {"cpu": self._cpu_limit, "memory_mb": self._memory_limit_mb},
            {"cpu": self._cpu_limit, "memory": self._memory_limit_mb},
            {"limits": {"cpu": self._cpu_limit, "memory_mb": self._memory_limit_mb}},
        ]
        for method_name in candidates:
            method = getattr(sandbox, method_name, None)
            if callable(method):
                for payload in payloads:
                    try:
                        method(**payload)
                        return
                    except TypeError:
                        continue
                    except Exception:
                        continue

        commands = getattr(sandbox, "commands", None)
        if commands:
            for method_name in ("set_limits", "configure", "configure_limits"):
                method = getattr(commands, method_name, None)
                if callable(method):
                    try:
                        method(cpu=self._cpu_limit, memory_mb=self._memory_limit_mb)
                        return
                    except Exception:
                        continue

    def _truncate_output(self, data: str) -> str:
        if self._max_output_bytes <= 0:
            return data
        encoded = data.encode("utf-8")
        if len(encoded) <= self._max_output_bytes:
            return data
        truncated = encoded[: self._max_output_bytes].decode("utf-8", errors="ignore")
        omitted = len(encoded) - self._max_output_bytes
        return f"{truncated}\n...[truncated {omitted} bytes]"
