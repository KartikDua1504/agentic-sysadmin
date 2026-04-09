"""
OpenEnv-compliant environment for Agentic Sysadmin.

This module implements the core reinforcement-learning environment that the
OpenEnv HTTP server wraps.  It extends ``Environment`` from
``openenv.core.env_server.interfaces`` so that ``create_app()`` can
automatically expose ``/reset``, ``/step``, ``/state``, ``/schema``, and
all other endpoints mandated by the OpenEnv runtime contract.

Architecture
------------
::

    ┌──────────────┐   HTTP/WS    ┌────────────┐   bash -lc   ┌───────────┐
    │  Agent / LLM │ ──────────▶  │  FastAPI    │ ──────────▶  │ Container │
    │              │ ◀──────────  │  (OpenEnv)  │ ◀──────────  │ Root FS   │
    └──────────────┘  Observation  └────────────┘   stdout     └───────────┘
                                        │
                                        ▼
                                  ┌────────────┐
                                  │ Task Grader │  (per-task scoring logic)
                                  └────────────┘

Key design decisions
--------------------
1. **Live-filesystem execution.**  Commands run against the real container
   OS via ``subprocess``, not a sandbox.  This is intentional — the tasks
   simulate genuine sysadmin break/fix scenarios.

2. **Pluggable graders.**  Each task ships its own ``grader.py`` with a
   ``grade(env, last_command)`` function.  The environment loads them
   dynamically via ``importlib`` so that adding a new task never requires
   touching this file.

3. **Score clamping.**  Rewards are clamped to (0.01, 0.99) to avoid
   degenerate edge cases in the evaluation pipeline (e.g. division by
   zero in normalisation).

4. **Task selection at reset time.**  The caller passes ``task_name`` as a
   keyword argument to ``reset()``; if omitted, the ``TASK_NAME``
   environment variable (or the first registered task) is used.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import EnvironmentMetadata

from env.models import SysAdminAction, SysAdminObservation, SysAdminState
from env.registry import TASK_REGISTRY

# Resolve once at import time; every path operation is relative to this root.
REPO_ROOT: Path = Path(__file__).resolve().parent.parent

# Public constant consumed by server/app.py for the /tasks endpoint.
AVAILABLE_TASKS: list[str] = list(TASK_REGISTRY.keys())

# Score is clamped to this open interval to prevent degenerate edge-case
# behaviour in downstream normalisation and leaderboard calculations.
_SCORE_FLOOR: float = 0.01
_SCORE_CEIL: float = 0.99


def _clamp_score(raw: float) -> float:
    """Clamp a raw grader score to the safe interval (FLOOR, CEIL).

    Args:
        raw: Unbounded score returned by a task grader.

    Returns:
        Score clamped to [_SCORE_FLOOR, _SCORE_CEIL].
    """
    return max(_SCORE_FLOOR, min(_SCORE_CEIL, float(raw)))


def _load_module_from_path(module_name: str, file_path: Path):
    """Import a Python module from an absolute filesystem path.

    This is used to load task-specific grader scripts at runtime without
    requiring them to be on ``sys.path`` or pre-registered in a package.

    Args:
        module_name: Arbitrary name used as the module's ``__name__``.
        file_path:   Absolute path to the ``.py`` file.

    Returns:
        The loaded module object.

    Raises:
        ImportError: If ``importlib`` cannot locate or parse the file.
    """
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SysAdminEnvironment(Environment):
    """OpenEnv ``Environment`` subclass for hostile-Linux sysadmin challenges.

    Lifecycle
    ---------
    1. ``__init__`` — lightweight; does **not** run setup scripts.
    2. ``reset(task_name=...)`` — loads the requested task's grader, executes
       its setup script against the container filesystem, and returns the
       initial observation.
    3. ``step(action)`` — executes the agent's command, invokes the grader,
       and returns an observation containing stdout, reward, and done flag.
    4. ``close()`` — no-op; cleanup is handled by container teardown.

    Thread safety
    -------------
    Instances are **not** thread-safe.  The OpenEnv server creates one
    instance per session (``max_concurrent_envs=1``), so this is fine.
    """

    def __init__(self) -> None:
        """Construct a new environment instance.

        The default task is read from the ``TASK_NAME`` environment variable
        (falling back to the first entry in ``TASK_REGISTRY``).  The actual
        setup script is **not** run here — that happens in ``reset()``.
        """
        super().__init__()
        self.task_name: str = os.getenv("TASK_NAME", AVAILABLE_TASKS[0])
        self.task_cfg: dict | None = None
        self.grader = None
        self.history: list[str] = []
        self.current_score: float = 0.5

        self._state = SysAdminState(
            episode_id=str(uuid4()),
            step_count=0,
            task_name=self.task_name,
            current_score=self.current_score,
            history_length=0,
        )

    # ------------------------------------------------------------------
    # Task loading
    # ------------------------------------------------------------------

    def _load_task(self, task_name: str) -> None:
        """Resolve and import the grader module for *task_name*.

        Args:
            task_name: Must be a key in ``TASK_REGISTRY``.

        Raises:
            ValueError:         If *task_name* is not registered.
            FileNotFoundError:  If the grader script does not exist on disk.
            AttributeError:     If the grader module lacks a ``grade`` function.
        """
        if task_name not in TASK_REGISTRY:
            raise ValueError(
                f"Task '{task_name}' not found. Available: {AVAILABLE_TASKS}"
            )

        self.task_name = task_name
        self.task_cfg = TASK_REGISTRY[task_name]

        grader_path = REPO_ROOT / self.task_cfg["grader_path"]
        if not grader_path.exists():
            raise FileNotFoundError(f"Missing grader file: {grader_path}")

        module = _load_module_from_path(f"tasks_{task_name}_grader", grader_path)

        if not hasattr(module, "grade"):
            raise AttributeError(
                f"Module '{grader_path}' is missing the required 'grade' function."
            )
        self.grader = getattr(module, "grade")

    # ------------------------------------------------------------------
    # Shell execution
    # ------------------------------------------------------------------

    def _run_command(self, command: str) -> tuple[int, str]:
        """Execute *command* in a login Bash shell on the host container.

        The command runs at ``cwd=/`` with the full inherited environment
        so that PATH, locale, and profile settings are consistent with
        what a human operator would see after ``ssh root@host``.

        Args:
            command: Raw Bash command string.

        Returns:
            Tuple of ``(exit_code, combined_output)`` where
            *combined_output* is stdout concatenated with stderr.

        Security:
            This executes **arbitrary code** on the container OS.  It is
            designed exclusively for controlled evaluation environments.
        """
        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd="/",
            capture_output=True,
            text=True,
            env={**os.environ},
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output

    def _run(self, command: str) -> str:
        """Convenience wrapper used by grader utility functions.

        Discards the exit code and returns only the combined output.
        """
        _, output = self._run_command(command)
        return output

    # ------------------------------------------------------------------
    # OpenEnv interface: reset / step / state
    # ------------------------------------------------------------------

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> SysAdminObservation:
        """Reset the environment for a new episode.

        Accepts ``task_name`` as a keyword argument (forwarded from the
        ``POST /reset`` JSON body).  If absent, falls back to the
        ``TASK_NAME`` environment variable, then to the first registered
        task.

        The task's ``setup.py`` script is executed against the live
        container filesystem to plant the deliberate misconfiguration
        that the agent must diagnose and fix.

        Args:
            seed:       Unused; accepted for OpenEnv interface compliance.
            episode_id: Optional caller-supplied episode identifier.
            **kwargs:   Must include ``task_name`` (str) to select the task.

        Returns:
            Initial ``SysAdminObservation`` with a welcome message and
            zero reward.

        Raises:
            ValueError:        If the requested task is not in the registry.
            FileNotFoundError: If the task's setup script is missing.
        """
        task_name = kwargs.get(
            "task_name",
            os.getenv("TASK_NAME", AVAILABLE_TASKS[0]),
        )

        self._load_task(task_name)

        # Execute the task-specific setup script to prepare the filesystem.
        # PermissionError is expected when running outside Docker (dev mode).
        setup_path = REPO_ROOT / self.task_cfg["setup_path"]
        if setup_path.exists():
            try:
                subprocess.run(
                    [sys.executable, str(setup_path)],
                    cwd=str(REPO_ROOT),
                    check=True,
                )
            except subprocess.CalledProcessError:
                pass  # Non-fatal: setup may fail outside a privileged container.

        # Reset episode bookkeeping.
        self.current_score = 0.5
        self.history = []

        self._state = SysAdminState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_name=self.task_name,
            current_score=self.current_score,
            history_length=0,
        )

        return SysAdminObservation(
            stdout=f"Environment initialized for task '{self.task_name}'. You are root.",
            stderr="",
            exit_code=0,
            cwd="/",
            done=False,
            reward=0.0,
            reasoning="Task loaded successfully.",
        )

    def step(
        self,
        action: SysAdminAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> SysAdminObservation:
        """Execute one agent action and return the resulting observation.

        Two code paths:

        * **"submit"** — The agent signals it believes the task is solved.
          The grader runs a final evaluation without executing a shell
          command, and ``done`` is forced to ``True``.

        * **Any other command** — The command is executed on the container,
          the grader evaluates the new filesystem state, and the resulting
          score and done flag are returned.

        Args:
            action:    ``SysAdminAction`` whose ``command`` field contains
                       the Bash command (or the literal string "submit").
            timeout_s: Unused; accepted for OpenEnv interface compliance.

        Returns:
            ``SysAdminObservation`` with stdout/stderr, exit code, reward
            (clamped to [0.01, 0.99]), done flag, and grader reasoning.
        """
        command = action.command.strip()

        # -- Submission path: grade final state, mark episode as done. ------
        if command.lower() == "submit":
            score, done, reason = self.grader(self, "submit")
            safe_score = _clamp_score(score)
            self.current_score = safe_score

            self._state.step_count += 1
            self._state.current_score = safe_score
            self._state.history_length = len(self.history)

            return SysAdminObservation(
                stdout="Submission evaluated.",
                stderr="",
                exit_code=0,
                cwd="/",
                done=True,
                reward=safe_score,
                reasoning=reason,
            )

        # -- Normal path: execute command, then grade. ----------------------
        exit_code, output = self._run_command(command)
        self.history.append(command)

        reward_val, done, reasoning = self.grader(self, command)
        safe_score = _clamp_score(reward_val)
        self.current_score = safe_score

        self._state.step_count += 1
        self._state.current_score = safe_score
        self._state.history_length = len(self.history)

        return SysAdminObservation(
            stdout=output if exit_code == 0 else "",
            stderr=output if exit_code != 0 else "",
            exit_code=exit_code,
            cwd="/",
            done=done,
            reward=safe_score,
            reasoning=reasoning,
        )

    @property
    def state(self) -> SysAdminState:
        """Return the current internal state snapshot.

        Consumed by the ``GET /state`` endpoint.
        """
        return self._state

    def get_metadata(self) -> EnvironmentMetadata:
        """Return static metadata about this environment.

        Consumed by the ``GET /metadata`` endpoint and used by the
        Gradio web UI when ``ENABLE_WEB_INTERFACE=true``.
        """
        return EnvironmentMetadata(
            name="agentic-sysadmin",
            description=(
                "Linux system administration challenges for AI agents. "
                "Agents must diagnose and fix misconfigured services on a "
                "live container."
            ),
            version="1.0.0",
        )

    def close(self) -> None:
        """Release resources held by this environment instance.

        Currently a no-op — the container lifecycle is managed externally
        by Docker / Hugging Face Spaces.  Provided for interface compliance.
        """
        pass
