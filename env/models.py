"""
Typed data models for the Agentic Sysadmin environment.

This module defines the Pydantic schemas that form the API contract between
the agent, the environment server, and the OpenEnv evaluation harness.

All models extend the canonical OpenEnv base types (Action, Observation, State)
so that ``create_app()`` can auto-generate JSON Schema endpoints at ``/schema``
and the framework can serialise/deserialise payloads without custom logic.

Design decisions
----------------
* ``SysAdminObservation`` carries both raw command output (stdout/stderr) and
  grading signals (reward, done, reasoning) in a single flat model.  This
  keeps the agent–server round-trip to one request per step.
* ``SysAdminState`` is intentionally lightweight — the real environment state
  lives on the container's filesystem.  The model only tracks metadata that
  the ``/state`` endpoint needs to return.
"""

from pydantic import Field
from openenv.core.env_server.types import Action, Observation, State


class SysAdminAction(Action):
    """An agent action requesting execution of a single shell command.

    Attributes:
        command: Arbitrary bash command string.  The environment executes it
                 via ``bash -lc`` on the container's root filesystem.
    """

    command: str = Field(
        ...,
        description="Bash command to execute on the container",
    )


class SysAdminObservation(Observation):
    """Observation returned after each ``step()`` or ``reset()`` call.

    Inherits ``done``, ``reward``, and ``metadata`` from the OpenEnv
    ``Observation`` base class.  Custom fields capture the shell output
    and the grader's qualitative reasoning.

    Attributes:
        stdout:    Standard output captured from the executed command.
        stderr:    Standard error captured from the executed command.
        exit_code: Process exit code (0 = success).
        cwd:       Working directory at the time of execution (always "/").
        reasoning: Human-readable explanation from the task grader describing
                   which checks passed or failed and why.
    """

    stdout: str = Field(default="", description="Standard output from the command")
    stderr: str = Field(default="", description="Standard error from the command")
    exit_code: int = Field(default=0, description="Exit code from the command")
    cwd: str = Field(default="/", description="Current working directory")
    reasoning: str = Field(default="", description="Grader reasoning for the score")


class SysAdminState(State):
    """Lightweight snapshot of the environment's internal bookkeeping.

    Returned by the ``GET /state`` endpoint.  Does **not** attempt to
    serialise the full container filesystem — that would be neither
    practical nor useful.  Instead it exposes just enough metadata for
    debugging and episode tracking.

    Attributes:
        task_name:      Identifier of the currently loaded task.
        current_score:  Most recent reward value produced by the grader.
        history_length: Number of commands the agent has executed so far.
    """

    task_name: str = Field(default="", description="Currently active task ID")
    current_score: float = Field(default=0.5, description="Current grading score")
    history_length: int = Field(default=0, description="Number of commands executed")
