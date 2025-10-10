import os

import pytest

from command_safety import analyze_command, dry_run_required


def test_safe_command_detection():
    result = analyze_command("echo", ["hello"])
    assert result.risk == "safe"
    assert result.reasons == []


def test_high_risk_command_detection():
    result = analyze_command("rm", ["-rf", "/"])
    assert result.risk == "caution"
    assert any("high risk" in reason.lower() for reason in result.reasons)


def test_blocking_metacharacters():
    result = analyze_command("sh", ["-c", "ls && rm -rf /"])
    assert result.risk == "block"


def test_dry_run_enforced(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGENT_HIGH_RISK_DRY_RUN", "1")
    result = analyze_command("rm", ["file.txt"])
    assert dry_run_required(result) is True
    monkeypatch.delenv("AGENT_HIGH_RISK_DRY_RUN", raising=False)
