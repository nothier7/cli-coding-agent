import textwrap

from patcher import validate_generated_code


def test_validate_generated_code_passes_for_valid_python():
    code = "def greet():\n    return 'hi'\n"
    issues = validate_generated_code("app.py", code)
    assert issues == []


def test_validate_generated_code_reports_python_syntax():
    code = "def bad(:\n    pass\n"
    issues = validate_generated_code("broken.py", code)
    assert issues
    assert "Python syntax error" in issues[0]


def test_validate_generated_code_reports_json_issue():
    issues = validate_generated_code("config.json", "{ not: valid }")
    assert issues
    assert "Invalid JSON" in issues[0]
