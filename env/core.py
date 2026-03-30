"""
Core orchestrator for the Agentic Sysadmin framework.
Spins up isolated Docker containers, executes agent commands, 
and routes the resulting system state to task-specific graders.
"""

import docker
import importlib
from typing import Dict, Any, Tuple

from env.models import SysAdminAction, SysAdminObservation, SysAdminReward
from env.registry import TASK_REGISTRY

class LinuxAdminEnv:
    def __init__(self, task_name):
        self.container = None
        self.task_name = task_name
        self.client = docker.from_env()

        if task_name not in TASK_REGISTRY:
            raise ValueError(f"Task '{task_name}' not found in registry.")

        module_name = TASK_REGISTRY[task_name]["grader_module"]
        module = importlib.import_module(module_name)

        if not hasattr(module, "grade"):
            raise AttributeError(f"Module '{module_name}' is missing the 'grade' function.")
        self.grader = getattr(module, "grade")

    def _get_obs(self) -> SysAdminObservation:
        return SysAdminObservation(
            stdout="Environment state captured.",
            stderr="",
            exit_code=0,
            cwd="/root",
        )
# Nuke any existing container from previous failed/aborted runs 
    def reset(self) -> SysAdminObservation:
        if self.container:
            try:
                self.container.stop(timeout=1)
                self.container.remove(force=True)
            except Exception:
                pass

        target_image = TASK_REGISTRY[self.task_name]["image"]

        self.container = self.client.containers.run(
            image=target_image,
            detach=True,
            tty=True,
        )

        self.current_score = 0.0
        self.history = []
        return self.state()

    def state(self) -> SysAdminObservation:
        if not self.container:
            return SysAdminObservation(stdout="", stderr="Container offline.", exit_code=-1, cwd="")

        exit_code, output = self.container.exec_run("pwd")
        cwd = output.decode("utf-8").strip() if exit_code == 0 else "/root"

        return SysAdminObservation(
            stdout="Container booted. You are root.",
            stderr="",
            exit_code=0,
            cwd=cwd,
        )

# Docker exec_run does not inherently persist environment state (like 'cd').
# Manually fetch the current working directory so the agent's spatial awareness stays intact.
    def step(self, action: SysAdminAction) -> Tuple[SysAdminObservation, SysAdminReward, bool, Dict[str, Any]]:
        if action.command.strip().lower() == "submit":
            score, done, reason = self.grader(self, "submit")
            return self._get_obs(), SysAdminReward(score=score, is_done=done, reasoning=reason), True, {}

        exec_result = self.container.exec_run(
            ["bash", "-c", action.command],
            workdir="/root",
        )

        output_raw = exec_result.output.decode("utf-8", errors="replace")
        stdout_str = output_raw if exec_result.exit_code == 0 else ""
        stderr_str = "" if exec_result.exit_code == 0 else output_raw

        _, pwd_out = self.container.exec_run("pwd")
        current_dir = pwd_out.decode("utf-8").strip()

        obs = SysAdminObservation(
            stdout=stdout_str,
            stderr=stderr_str,
            exit_code=exec_result.exit_code,
            cwd=current_dir,
        )

        self.history.append(action.command)

        reward_val, done, reasoning = self.grader(self, action.command)
        reward = SysAdminReward(score=reward_val, is_done=done, reasoning=reasoning)

        return obs, reward, done, {}

    def _run(self, command: str) -> str:
    """
    A silent execution helper specifically built for Graders.
    Allows the grading logic to probe the container (e.g., check file existence) 
    without polluting the agent's stdout/stderr history.
    Also handles the Docker SDK's inconsistent return types (bytes vs tuples).
    """
        if self.container is None:
            raise RuntimeError("Container is not running")

        result = self.container.exec_run(["/bin/bash", "-c", command])
        output = result.output
        if isinstance(output, bytes):
            return output.decode("utf-8", errors="replace")
        if isinstance(output, tuple):
            stdout = output[0] or b""
            stderr = output[1] or b""
            return (stdout + stderr).decode("utf-8", errors="replace")
        return str(output)
