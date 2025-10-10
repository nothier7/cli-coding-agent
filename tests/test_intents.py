import pytest

from intents import parse_intent, EditFile, CreateFile, RunCommand


def test_parse_edit_file_intent():
    payload = {
        "type": "edit_file",
        "path": "src/app.py",
        "instructions": "Update the greeting text",
        "patch": None,
    }
    intent = parse_intent(payload)
    assert isinstance(intent, EditFile)
    assert intent.path == "src/app.py"
    assert intent.instructions == "Update the greeting text"
    assert intent.patch is None


def test_parse_create_file_intent():
    payload = {
        "type": "create_file",
        "path": "src/new_module.py",
        "contents": "# new module",
    }
    intent = parse_intent(payload)
    assert isinstance(intent, CreateFile)
    assert intent.path == "src/new_module.py"
    assert intent.contents.startswith("# new module")


def test_parse_run_command_intent():
    payload = {
        "type": "run_command",
        "command": "pytest",
        "args": ["-q"],
    }
    intent = parse_intent(payload)
    assert isinstance(intent, RunCommand)
    assert intent.command == "pytest"
    assert intent.args == ["-q"]


def test_parse_intent_rejects_unknown_type():
    with pytest.raises(ValueError):
        parse_intent({"type": "unknown"})
