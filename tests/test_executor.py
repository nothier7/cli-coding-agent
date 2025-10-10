import pytest

from executor import ensure_safe_arguments


def test_ensure_safe_arguments_blocks_shell_control_tokens():
    with pytest.raises(PermissionError):
        ensure_safe_arguments("bash", ["-c", "ls"])


def test_ensure_safe_arguments_blocks_metacharacters():
    with pytest.raises(PermissionError):
        ensure_safe_arguments("python", ["&& rm -rf /"])


def test_ensure_safe_arguments_accepts_safe_args():
    ensure_safe_arguments("python", ["-m", "pip", "--version"])
