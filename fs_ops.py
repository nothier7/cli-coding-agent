# fs_ops.py
from pathlib import Path
from typing import Optional, Tuple
import difflib

def read_file_text(path: str) -> Tuple[bool, Optional[str], Optional[str]]:
    p = Path(path)
    if not p.exists():
        return False, None, f"File not found: {path}"
    try:
        return True, p.read_text(encoding="utf-8"), None
    except Exception as e:
        return False, None, f"Failed to read {path}: {e}"

def write_file_text(path: str, contents: str) -> Tuple[bool, Optional[str]]:
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(contents, encoding="utf-8")
        return True, None
    except Exception as e:
        return False, f"Failed to write {path}: {e}"

def compute_unified_diff(old: str, new: str, path: str) -> str:
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines, new_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm=""
    )
    return "".join(diff)
