# memory.py
import json
from pathlib import Path
from typing import Literal, List, TypedDict

AGENT_DIR = Path(".agent")
SESSION_FILE = AGENT_DIR / "session.json"


class Turn(TypedDict):
    role: Literal["user", "assistant"]
    content: str


def load_memory() -> List[Turn]:
    AGENT_DIR.mkdir(exist_ok=True)
    if not SESSION_FILE.exists():
        return []
    return json.loads(SESSION_FILE.read_text())


def save_memory(turns: List[Turn]) -> None:
    AGENT_DIR.mkdir(exist_ok=True)
    SESSION_FILE.write_text(json.dumps(turns, indent=2))
