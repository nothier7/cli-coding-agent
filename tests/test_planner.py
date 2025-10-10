import pytest

from planner import plan_from_intent


def test_plan_for_create_file():
    intent = {
        "type": "create_file",
        "path": "docs/readme.md",
        "contents": "# Hello\n",
    }
    plan = plan_from_intent(intent)
    assert plan == [
        {"kind": "show_diff", "path": "docs/readme.md", "contents": "# Hello\n"},
        {"kind": "write_file", "path": "docs/readme.md", "contents": "# Hello\n"},
    ]


def test_plan_for_edit_file_without_patch(tmp_path, monkeypatch):
    project_dir = tmp_path / "proj"
    target = project_dir / "src/app.py"
    target.parent.mkdir(parents=True)
    target.write_text("print('hi')\n", encoding="utf-8")
    monkeypatch.chdir(project_dir)

    intent = {
        "type": "edit_file",
        "path": "src/app.py",
        "instructions": "Refactor greet()",
        "patch": None,
    }
    plan = plan_from_intent(intent)
    assert plan[0] == {"kind": "read_file", "path": "src/app.py"}
    assert plan[1] == {
        "kind": "synthesize_patch",
        "path": "src/app.py",
        "instructions": "Refactor greet()",
    }
    assert plan[2] == {"kind": "show_diff", "path": "src/app.py"}
    assert plan[3] == {"kind": "write_file", "path": "src/app.py"}


def test_plan_for_edit_file_with_patch(tmp_path, monkeypatch):
    project_dir = tmp_path / "proj"
    target = project_dir / "src/app.py"
    target.parent.mkdir(parents=True)
    target.write_text("print('hi')\n", encoding="utf-8")
    monkeypatch.chdir(project_dir)

    intent = {
        "type": "edit_file",
        "path": "src/app.py",
        "instructions": "Already provided diff",
        "patch": "diff --git a/src/app.py b/src/app.py\n",
    }
    plan = plan_from_intent(intent)
    assert plan == [
        {"kind": "read_file", "path": "src/app.py"},
        {
            "kind": "show_diff",
            "path": "src/app.py",
            "contents": "diff --git a/src/app.py b/src/app.py\n",
        },
        {
            "kind": "write_file",
            "path": "src/app.py",
            "contents": "diff --git a/src/app.py b/src/app.py\n",
        },
    ]


def test_plan_for_run_command():
    intent = {
        "type": "run_command",
        "command": "ls",
        "args": ["-l"],
    }
    plan = plan_from_intent(intent)
    assert plan == [
        {"kind": "run_command", "command": "ls", "args": ["-l"]}
    ]


def test_plan_rejects_unknown_type():
    with pytest.raises(ValueError):
        plan_from_intent({"type": "delete_file"})


def test_plan_returns_error_when_file_missing(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    intent = {
        "type": "edit_file",
        "path": "does/not/exist.py",
        "instructions": "irrelevant",
        "patch": None,
    }
    plan = plan_from_intent(intent)
    assert plan == [
        {"kind": "error", "path": "does/not/exist.py", "message": "Target file 'does/not/exist.py' does not exist."}
    ]
