#!/usr/bin/env python3
"""
Single-task runner for demo recordings — **Docker-isolated** edition.

Usage
-----
    python run_task.py <task_id>

Examples
--------
    python run_task.py 2k_vs_200k
    python run_task.py authoritarian_ssh
    python run_task.py ls_cat_trivia
    python run_task.py math_is_not_mathing
    python run_task.py mmap_exhaustion
    python run_task.py pls_adopt_me

Instead of running setup scripts and agent commands directly on the host
(which requires root and can corrupt the machine), this script:

1. Builds a Docker image from the project Dockerfile.
2. Starts a privileged container that stays running.
3. Copies the project source into the container.
4. Patches `SysAdminEnvironment._run_command` so **every** shell
   invocation (setup, agent steps, grader checks) goes through
   `docker exec` into the container.
5. Cleans up (stops + removes) the container on exit.

Required `.env` keys
--------------------
    API_KEY          – Your GitHub PAT (ghp_...) or any OpenAI-compatible key.
    API_BASE_URL     – (optional) defaults to GitHub Models endpoint.
    MODEL_NAME       – (optional) defaults to gpt-4o-mini.
    MAX_STEPS        – (optional) defaults to 30.
    TEMPERATURE      – (optional) defaults to 0.0.
    MAX_TOKENS       – (optional) defaults to 700.
"""

import atexit
import os
import signal
import subprocess
import sys
import pathlib
import time

# ---------------------------------------------------------------------------
# Load .env file manually (no extra dependencies)
# ---------------------------------------------------------------------------

def load_dotenv(env_path: str = ".env") -> None:
    """Parse a .env file and inject its values into ``os.environ``.

    Only sets a variable if it is not already defined in the real
    environment, so real env vars always take precedence.
    """
    path = pathlib.Path(env_path)
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# Load .env BEFORE any other imports that rely on env vars.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent
load_dotenv(str(_REPO_ROOT / ".env"))

# ---------------------------------------------------------------------------
# Available tasks (duplicated here to avoid import-time side effects)
# ---------------------------------------------------------------------------

TASKS = [
    "2k_vs_200k",
    "authoritarian_ssh",
    "ls_cat_trivia",
    "math_is_not_mathing",
    "mmap_exhaustion",
    "pls_adopt_me",
]

DOCKER_IMAGE = "agentic-sysadmin"
DOCKER_CONTAINER = "agentic-sysadmin-runner"


def print_usage() -> None:
    print("\n╔═══════════════════════════════════════════════════════╗")
    print("║   Agentic Sysadmin – Dockerised Single Task Runner  ║")
    print("╚═══════════════════════════════════════════════════════╝\n")
    print("Usage:  python run_task.py <task_id>\n")
    print("Available tasks:")
    for t in TASKS:
        print(f"  • {t}")
    print()


# ---------------------------------------------------------------------------
# Docker helpers
# ---------------------------------------------------------------------------

def _sh(cmd: list[str], *, check: bool = True, quiet: bool = False, **kw) -> subprocess.CompletedProcess:
    """Run a host command, optionally suppressing stdout."""
    if quiet:
        kw.setdefault("stdout", subprocess.DEVNULL)
    return subprocess.run(cmd, text=True, **kw)


def docker_build() -> None:
    """Build the Docker image from the project Dockerfile."""
    print("  🐳  Building Docker image …")
    result = _sh(
        ["docker", "build", "-t", DOCKER_IMAGE, "."],
        cwd=str(_REPO_ROOT),
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"  ❌ Docker build failed:\n{result.stderr}")
        sys.exit(1)
    print("  ✅  Image built.")


def docker_start() -> None:
    """Start the container (detached, privileged, sleeping forever)."""
    # Remove any leftover container with the same name.
    _sh(["docker", "rm", "-f", DOCKER_CONTAINER], check=False, quiet=True,
         stderr=subprocess.DEVNULL)

    print("  🐳  Starting container …")
    result = _sh(
        [
            "docker", "run", "-d",
            "--name", DOCKER_CONTAINER,
            "--privileged",
            DOCKER_IMAGE,
            "sleep", "infinity",
        ],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"  ❌ Container start failed:\n{result.stderr}")
        sys.exit(1)
    print(f"  ✅  Container '{DOCKER_CONTAINER}' running.")


def docker_stop() -> None:
    """Stop and remove the container (best-effort, safe to call twice)."""
    print(f"\n  🧹 Cleaning up container '{DOCKER_CONTAINER}' …")
    _sh(["docker", "rm", "-f", DOCKER_CONTAINER],
        check=False, quiet=True, stderr=subprocess.DEVNULL)


def docker_exec(command: str) -> tuple[int, str]:
    """Execute *command* inside the running container via ``docker exec``.

    Returns (exit_code, combined_stdout_stderr).
    """
    proc = subprocess.run(
        ["docker", "exec", DOCKER_CONTAINER, "bash", "-lc", command],
        capture_output=True,
        text=True,
    )
    output = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, output


def docker_exec_script(script_path: str) -> int:
    """Run a Python script inside the container.

    *script_path* is the path **inside the container** (e.g. /app/tasks/…/setup.py).
    """
    proc = subprocess.run(
        ["docker", "exec", DOCKER_CONTAINER, "python3", script_path],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        # Print stderr if the setup script fails so we can debug.
        print(f"  ⚠️  Script exited {proc.returncode}: {proc.stderr.strip()}")
    return proc.returncode


# ---------------------------------------------------------------------------
# Monkey-patch the environment to run commands inside Docker
# ---------------------------------------------------------------------------

def _patch_environment(env):
    """Replace ``env._run_command`` so all shell commands and grader
    checks happen inside the Docker container instead of on the host."""

    def _dockerised_run_command(command: str) -> tuple[int, str]:
        return docker_exec(command)

    # Patch the instance method.
    import types
    env._run_command = types.MethodType(lambda self, cmd: docker_exec(cmd), env)

    # Also patch _run (used by grader_utils).
    original_run = env._run
    def _dockerised_run(command: str) -> str:
        _, output = docker_exec(command)
        return output
    env._run = types.MethodType(lambda self, cmd: docker_exec(cmd)[1], env)


def _patch_reset_to_use_docker(env, repo_root: pathlib.Path):
    """Patch ``env.reset`` so that the setup script is executed inside Docker
    instead of via host subprocess."""
    import types
    from uuid import uuid4

    original_load_task = env._load_task

    def patched_reset(self, seed=None, episode_id=None, **kwargs):
        from env.models import SysAdminObservation
        from env.registry import TASK_REGISTRY

        task_name = kwargs.get(
            "task_name",
            os.getenv("TASK_NAME", list(TASK_REGISTRY.keys())[0]),
        )

        # Load grader locally (it will use our patched _run_command).
        self._load_task(task_name)

        # Execute the setup script INSIDE the container.
        setup_rel = self.task_cfg["setup_path"]  # e.g. tasks/authoritarian_ssh/setup.py
        container_setup = f"/app/{setup_rel}"
        print(f"  🐳  Running setup script in container: {container_setup}")
        docker_exec_script(container_setup)

        # Reset bookkeeping.
        self.current_score = 0.5
        self.history = []

        from env.models import SysAdminState
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

    env.reset = types.MethodType(patched_reset, env)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_usage()
        sys.exit(0)

    task_id = sys.argv[1].strip()

    if task_id not in TASKS:
        print(f"\n❌  Unknown task: '{task_id}'\n")
        print_usage()
        sys.exit(1)

    # ── Resolve credentials ────────────────────────────────────────────
    api_key = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
    if not api_key:
        print("❌  No API key found. Set API_KEY or HF_TOKEN in your .env file.")
        sys.exit(1)

    api_base = os.getenv("API_BASE_URL", "https://models.inference.ai.azure.com")
    model    = os.getenv("MODEL_NAME", "gpt-4o-mini")
    max_steps   = int(os.getenv("MAX_STEPS", "30"))
    temperature = float(os.getenv("TEMPERATURE", "0.0"))
    max_tokens  = int(os.getenv("MAX_TOKENS", "700"))

    print("\n╔═══════════════════════════════════════════════════════╗")
    print("║   Agentic Sysadmin – Dockerised Single Task Runner  ║")
    print("╚═══════════════════════════════════════════════════════╝\n")
    print(f"  Task       : {task_id}")
    print(f"  Model      : {model}")
    print(f"  API Base   : {api_base}")
    print(f"  Max Steps  : {max_steps}")
    print(f"  Temperature: {temperature}")
    print(f"  Max Tokens : {max_tokens}")
    print(f"  Key        : {api_key[:8]}...{api_key[-4:]}")
    print()

    # ── Docker setup ───────────────────────────────────────────────────
    docker_build()
    docker_start()

    # Make sure the container is always cleaned up.
    atexit.register(docker_stop)
    signal.signal(signal.SIGINT,  lambda *_: sys.exit(1))
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(1))

    # ── Inject TASK_NAME so downstream code picks it up ────────────────
    os.environ["TASK_NAME"] = task_id

    # ── Now import the heavy modules (after env is configured) ─────────
    from openai import OpenAI, RateLimitError
    from env.core import SysAdminEnvironment
    from env.models import SysAdminAction
    from inference import (
        SYSTEM_PROMPT,
        build_user_prompt,
        get_task_brief,
        parse_model_action,
    )

    # ── Build client & environment ─────────────────────────────────────
    client = OpenAI(base_url=api_base, api_key=api_key)
    env    = SysAdminEnvironment()

    # Patch the environment so ALL execution goes into Docker.
    _patch_environment(env)
    _patch_reset_to_use_docker(env, _REPO_ROOT)

    # ── Run the task ───────────────────────────────────────────────────
    print(f"\n{'─'*55}")
    print(f"[START] task={task_id}")
    print(f"{'─'*55}\n")

    brief = get_task_brief(task_id)
    obs   = env.reset(task_name=task_id)
    history: list[str] = []
    current_score: float = 0.5

    for step in range(1, max_steps + 1):
        prompt = build_user_prompt(step, obs, brief, history)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ]

        # ── Call LLM with retry ────────────────────────────────────────
        raw = None
        for attempt in range(5):
            try:
                completion = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                raw = completion.choices[0].message.content or "pwd"
                break
            except RateLimitError:
                wait = 5 * (2 ** attempt)
                print(f"  ⏳ Rate-limited – waiting {wait}s ...")
                time.sleep(wait)
            except Exception as e:
                print(f"  ❌ API error: {e}")
                print(f"\n[END] task={task_id} score={current_score} steps={step}")
                sys.exit(1)

        if raw is None:
            print("  ❌ Max retries exceeded.")
            print(f"\n[END] task={task_id} score={current_score} steps={step}")
            sys.exit(1)

        cmd = parse_model_action(raw)
        print(f"  [{step:>2}/{max_steps}]  $ {cmd}")

        obs = env.step(SysAdminAction(command=cmd))
        history.append(f"{cmd} → {obs.exit_code}")

        current_score = float(obs.reward) if obs.reward is not None else current_score
        current_score = max(0.01, min(0.99, current_score))

        status = "✅" if obs.done else "⏳"
        print(f"           {status}  reward={current_score:.2f}  done={obs.done}")

        if obs.done:
            break

        time.sleep(2.0)

    # ── Summary ────────────────────────────────────────────────────────
    final_step = min(step, max_steps)
    print(f"\n{'─'*55}")
    print(f"[END] task={task_id} score={current_score:.2f} steps={final_step}")
    print(f"{'─'*55}\n")

    if current_score >= 0.9:
        print("🎉  Task solved!")
    elif current_score >= 0.5:
        print("⚠️   Partial progress.")
    else:
        print("❌  Task not solved.")


if __name__ == "__main__":
    main()
