"""
Local orchestrator for Agentic Sysadmin.
Executes tasks natively on the container's real root file system.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

from env.models import SysAdminAction, SysAdminObservation, SysAdminReward
from env.registry import TASK_REGISTRY

REPO_ROOT = Path(__file__).resolve().parent.parent

def _load_module_from_path(module_name: str, file_path: Path):
    """
    Dynamically loads a Python module from a file path.

    Used to load task-specific grader scripts at runtime.

    Assumptions:
    - The target file is a valid Python module
    - The module defines a `grade(env, command)` function

    Why dynamic loading:
    - Tasks are pluggable and defined outside core environment code
    - Avoids hardcoding task logic into the environment
    """
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class LinuxAdminEnv:
    """
    Reinforcement-learning-style environment for sysadmin tasks.

    This environment allows an agent to:
    - Execute arbitrary shell commands on the host container (root FS)
    - Observe stdout/stderr and exit codes
    - Receive rewards via a task-specific grader

    Core concepts:
    - State: Implicitly represented by the live filesystem + system state
    - Action: A bash command (SysAdminAction.command)
    - Observation: Command output + exit status
    - Reward: Computed dynamically via a task-specific grading function

    Important:
    - Commands execute on the *real* container OS, not a sandbox
    - Grader functions define task success and scoring
    """
    def __init__(self, task_name: str):
        if task_name not in TASK_REGISTRY:
            raise ValueError(f"Task '{task_name}' not found in registry.")

        self.task_name = task_name
        self.task_cfg = TASK_REGISTRY[task_name]
        self.history = []
        self.current_score = 0.0

        grader_path = REPO_ROOT / self.task_cfg["grader_path"]
        if not grader_path.exists():
            raise FileNotFoundError(f"Missing grader file: {grader_path}")

        module = _load_module_from_path(
            f"tasks_{task_name}_grader",
            grader_path,
        )

        if not hasattr(module, "grade"):
            raise AttributeError(f"Module '{grader_path}' is missing the 'grade' function.")

        self.grader = getattr(module, "grade")

    def _run_command(self, command: str) -> Tuple[int, str]:
        """
        Execute a shell command in a login bash shell on the host container.

        Details:
        - Uses `bash -lc` to ensure:
        - Login shell semantics (profile, rc files)
        - Consistent environment resolution
        - Executes at root directory (`cwd="/"`) to simulate system-level access
        - Inherits current environment variables

        Returns:
            (exit_code, combined stdout + stderr output)

        Security note:
        - This executes arbitrary commands on the container OS.
        - Intended for controlled evaluation environments only.
        """
        proc = subprocess.run(
            ["bash", "-lc", command],
            cwd="/",  # Force execution at native root
            capture_output=True,
            text=True,
            env={**os.environ},
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, output

    def reset(self) -> SysAdminObservation:
        """
        Resets the environment to its initial state for the current task.

        Executes the task-specific setup script directly against the live container OS 
        to prepare the file system and services. It also wipes the internal agent state, 
        clearing the command history and resetting the current score.

        Returns:
            SysAdminObservation: The initial observation indicating the environment 
            is ready, simulating a fresh root shell starting point.

        Raises:
            FileNotFoundError: If the task's setup script cannot be located.
            subprocess.CalledProcessError: If the setup script fails during execution.
        """
        setup_path = REPO_ROOT / self.task_cfg["setup_path"]
        if not setup_path.exists():
            raise FileNotFoundError(f"Missing setup file: {setup_path}")

        subprocess.run(
            [sys.executable, str(setup_path)],
            cwd=str(REPO_ROOT),
            check=True,
        )

        self.current_score = 0.0
        self.history = []
        
        return SysAdminObservation(
            stdout="Environment initialized. You are root.",
            stderr="",
            exit_code=0,
            cwd="/",
        )

    def step(
        self, action: SysAdminAction
    ) -> Tuple[SysAdminObservation, SysAdminReward, bool, Dict[str, Any]]:
        command = action.command.strip()
        """
        Executes a single agent action (shell command) and advances the environment state.

        If the command is 'submit', it triggers the final grading evaluation without 
        running a shell command. Otherwise, it executes the command against the live OS, 
        captures the output, and dynamically grades the new state.

        Args:
            action (SysAdminAction): The action containing the bash command to execute.

        Returns:
            Tuple containing:
            - observation (SysAdminObservation): The stdout/stderr and exit code.
            - reward (SysAdminReward): The current score and grading reasoning.
            - done (bool): True if the task is complete or submitted, False otherwise.
            - info (Dict): Additional diagnostic information (currently empty).
        """
        if command.lower() == "submit":
            score, done, reason = self.grader(self, "submit")
            return SysAdminObservation(stdout="", stderr="", exit_code=0, cwd="/"), \
                   SysAdminReward(score=score, is_done=done, reasoning=reason), True, {}

        exit_code, output = self._run_command(command)
        obs = SysAdminObservation(
            stdout=output if exit_code == 0 else "",
            stderr="" if exit_code != 0 else output,
            exit_code=exit_code,
            cwd="/",
        )

        self.history.append(command)

        reward_val, done, reasoning = self.grader(self, command)
        self.current_score = reward_val
        reward = SysAdminReward(score=reward_val, is_done=done, reasoning=reasoning)

        return obs, reward, done, {}

    def _run(self, command: str) -> str:
        _, output = self._run_command(command)
        return output
