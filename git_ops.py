# git_ops.py
import subprocess
from pathlib import Path
from typing import Optional, List, Tuple

def _run(args: List[str], cwd: Optional[str] = None) -> Tuple[int, str, str]:
    p = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr

def ensure_repo(root: str = ".") -> None:
    if not (Path(root) / ".git").exists():
        code, out, err = _run(["git", "init"], cwd=root)
        if code != 0:
            raise RuntimeError(f"git init failed: {err or out}")
        # initial commit (optional)
        _run(["git", "add", "-A"], cwd=root)
        _run(["git", "commit", "-m", "chore(agent): init repo"], cwd=root)

def commit_paths(paths: List[str], message: str, root: str = ".") -> None:
    code, out, err = _run(["git", "add", *paths], cwd=root)
    if code != 0:
        raise RuntimeError(f"git add failed: {err or out}")
    code, out, err = _run(["git", "commit", "-m", message], cwd=root)
    if code != 0:
        raise RuntimeError(f"git commit failed: {err or out}")

def rollback_last(root: str = ".") -> None:
    code, out, err = _run(["git", "reset", "--hard", "HEAD~1"], cwd=root)
    if code != 0:
        raise RuntimeError(f"git reset failed: {err or out}")
