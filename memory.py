# memory.py
import json
from pathlib import Path
from typing import Literal, List, TypedDict

MAX_TURNS = 40

AGENT_DIR = Path(".agent")
SESSION_FILE = AGENT_DIR / "session.json"


class Turn(TypedDict):
    role: Literal["user", "assistant"]
    content: str


def load_memory() -> List[Turn]:
    AGENT_DIR.mkdir(exist_ok=True)
    if not SESSION_FILE.exists():
        return []
    try:
        data = json.loads(SESSION_FILE.read_text())
    except json.JSONDecodeError:
        return []

    turns: List[Turn] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = item.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            turns.append({"role": role, "content": content})
    return turns[-MAX_TURNS:]


def save_memory(turns: List[Turn]) -> None:
    AGENT_DIR.mkdir(exist_ok=True)
    sanitized: List[Turn] = []
    for turn in turns[-MAX_TURNS:]:
        role = turn.get("role")
        content = turn.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            sanitized.append({"role": role, "content": content})
    SESSION_FILE.write_text(json.dumps(sanitized, indent=2))
