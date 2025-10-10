# planner.py
from pathlib import Path
from typing import Dict, Any, List, TypedDict, Literal, Optional

class Step(TypedDict, total=False):
    kind: Literal["read_file", "synthesize_patch", "show_diff", "write_file", "run_command", "error"]
    path: Optional[str]
    contents: Optional[str]
    instructions: Optional[str]
    command: Optional[str]
    args: Optional[List[str]]
    message: Optional[str]

def plan_from_intent(intent: Dict[str, Any]) -> List[Step]:
    t = intent.get("type")
    if t == "create_file":
        return [
            {"kind": "show_diff", "path": intent["path"], "contents": intent["contents"]},
            {"kind": "write_file", "path": intent["path"], "contents": intent["contents"]},
        ]
    if t == "edit_file":
        path = intent["path"]
        if not Path(path).exists():
            return [
                {"kind": "error", "path": path, "message": f"Target file '{path}' does not exist."}
            ]
        steps: List[Step] = [{"kind": "read_file", "path": path}]
        if intent.get("patch"):
            steps += [
                {"kind": "show_diff", "path": path, "contents": intent["patch"]},
                {"kind": "write_file", "path": path, "contents": intent["patch"]},
            ]
        else:
            steps += [
                {"kind": "synthesize_patch", "path": path, "instructions": intent["instructions"]},
                {"kind": "show_diff", "path": path},   # contents will be filled at runtime
                {"kind": "write_file", "path": path},   # contents will be filled at runtime
            ]
        return steps
    if t == "run_command":
        return [{"kind": "run_command", "command": intent["command"], "args": intent.get("args", [])}]
    raise ValueError(f"Unsupported intent type in planner: {t}")
