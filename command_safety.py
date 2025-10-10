from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import List, Sequence, Literal


RiskLevel = Literal["safe", "caution", "block"]

# Commands that routinely perform irreversible mutations.
HIGH_RISK_COMMANDS = {
    "rm",
    "rmdir",
    "del",
    "erase",
    "mv",
    "move",
    "cp",
    "copy",
    "dd",
    "chmod",
    "chown",
    "kill",
    "pkill",
    "killall",
    "shutdown",
    "reboot",
    "mkfs",
    "diskpart",
    "format",
    "docker",
    "kubectl",
    "systemctl",
}

# Shell metacharacters that indicate control flow or redirection.
BLOCKING_PATTERNS = [
    r";",
    r"\|\|",
    r"&&",
    r"\|",
    r"`",
    r"\$\(",
]

CAUTION_PATTERNS = [
    r">",
    r"<",
]

FORCE_FLAGS = {"-f", "--force", "-rf", "-fr", "/f"}
RECURSIVE_FLAGS = {"-r", "-R", "--recursive", "/s"}
ROOT_PATHS = {"/", "C:\\", "C:/"}
SHELL_COMMANDS = {"sh", "bash", "zsh", "fish", "cmd", "cmd.exe", "powershell", "pwsh"}
SHELL_EXECUTE_FLAGS = {"-c", "/c"}


@dataclass
class CommandSafetyResult:
    risk: RiskLevel = "safe"
    reasons: List[str] = field(default_factory=list)

    def downgrade_to_block(self, reason: str) -> None:
        self.risk = "block"
        self.reasons.append(reason)

    def elevate_to_caution(self, reason: str) -> None:
        if self.risk != "block":
            self.risk = "caution"
        self.reasons.append(reason)


def analyze_command(cmd: str, args: Sequence[str]) -> CommandSafetyResult:
    result = CommandSafetyResult()
    command_name = os.path.basename(cmd).lower()
    full_text = " ".join([cmd] + list(args))

    for pattern in BLOCKING_PATTERNS:
        if re.search(pattern, full_text):
            result.downgrade_to_block("Shell control operators are not permitted in agent-managed commands.")
            break

    if result.risk != "block":
        for pattern in CAUTION_PATTERNS:
            if re.search(pattern, full_text):
                result.elevate_to_caution("Shell redirection was detected; review carefully before execution.")
                break

    if command_name in HIGH_RISK_COMMANDS:
        result.elevate_to_caution(f"Command '{command_name}' is considered high risk.")

    lowered_args = {arg.lower() for arg in args}
    if FORCE_FLAGS.intersection(lowered_args):
        result.elevate_to_caution("Force flag detected; this can bypass safety prompts.")
    if RECURSIVE_FLAGS.intersection(lowered_args):
        result.elevate_to_caution("Recursive flag detected; review target paths carefully.")

    if command_name in SHELL_COMMANDS and SHELL_EXECUTE_FLAGS.intersection(lowered_args):
        result.downgrade_to_block("Shell execution with '-c' is disabled for safety.")

    for arg in args:
        normalized = arg.strip('"').strip("'")
        if normalized in ROOT_PATHS:
            result.elevate_to_caution("Command targets the filesystem root.")
        if normalized.startswith(("/", "~/", "C:/", "C:\\")) and command_name in {"rm", "del", "erase", "rmdir"}:
            result.elevate_to_caution("Deleting from an absolute path is high risk.")

    return result


def dry_run_required(result: CommandSafetyResult) -> bool:
    env = os.getenv("AGENT_HIGH_RISK_DRY_RUN", "").strip().lower()
    if env in {"1", "true", "yes"} and result.risk != "safe":
        return True
    return False
