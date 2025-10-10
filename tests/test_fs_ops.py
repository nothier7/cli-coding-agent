from pathlib import Path

import pytest

from fs_ops import read_file_text, write_file_text, compute_unified_diff


def test_write_and_read_roundtrip(tmp_path: Path):
    target = tmp_path / "example.txt"
    ok, err = write_file_text(str(target), "hello world\n")
    assert ok is True
    assert err is None

    read_ok, contents, read_err = read_file_text(str(target))
    assert read_ok is True
    assert contents == "hello world\n"
    assert read_err is None


def test_read_missing_file(tmp_path: Path):
    target = tmp_path / "missing.txt"
    ok, contents, err = read_file_text(str(target))
    assert ok is False
    assert contents is None
    assert "File not found" in err


def test_compute_unified_diff_matches_golden():
    before = "print('hello')\n"
    after = "print('hello world')\n"
    diff = compute_unified_diff(before, after, "app.py")
    expected = (
        "--- a/app.py\n"
        "+++ b/app.py\n"
        "@@ -1 +1 @@\n"
        "-print('hello')\n"
        "+print('hello world')\n"
    )
    assert diff == expected
