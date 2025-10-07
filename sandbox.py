# sandbox.py
from __future__ import annotations
import json
from pathlib import Path
from typing import List, Tuple, Protocol

SANDBOX_CONF = Path(".agent/sandbox.json")

class Sandbox(Protocol):
    def run(self, command: str, args: List[str]) -> Tuple[int, str, str]:
        ...

    def close(self) -> None:
        ...

def _read_conf() -> dict:
    if SANDBOX_CONF.exists():
        try:
            return json.loads(SANDBOX_CONF.read_text())
        except Exception:
            pass
    # default conf
    conf = {"provider": "local"}
    SANDBOX_CONF.parent.mkdir(exist_ok=True)
    SANDBOX_CONF.write_text(json.dumps(conf, indent=2))
    return conf

def make_sandbox() -> Sandbox:
    conf = _read_conf()
    provider = conf.get("provider", "local").lower()
    if provider == "local":
        from providers.local_sandbox import LocalSandbox
        return LocalSandbox()
    elif provider == "e2b":
        from providers.e2b_sandbox import E2BSandbox
        return E2BSandbox()
    else:
        # fallback to local
        from providers.local_sandbox import LocalSandbox
        return LocalSandbox()
