"""
Lightweight data schemas for Agentic Sysadmin.
No external dependencies (removed pydantic).
"""

from dataclasses import dataclass


@dataclass
class SysAdminAction:
    command: str


@dataclass
class SysAdminObservation:
    stdout: str
    stderr: str
    exit_code: int
    cwd: str


@dataclass
class SysAdminReward:
    score: float
    is_done: bool
    reasoning: str
