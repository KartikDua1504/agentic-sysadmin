#!/usr/bin/env python3
"""
LLM-driven inference loop for Agentic Sysadmin tasks.

This script is the submission entry point evaluated by the hackathon pipeline.
It instantiates the environment, resets it for a target task, and runs a
multi-turn agent loop where an LLM issues one shell command per step.

Execution flow
--------------
1. Read configuration from environment variables (see below).
2. Instantiate ``SysAdminEnvironment`` and reset with the target task.
3. For each step up to ``MAX_STEPS``:
   a. Build a prompt containing the task brief, command history, and
      current observation.
   b. Query the LLM for the next bash command.
   c. Execute the command via ``env.step()``.
   d. Log the step in ``[STEP]`` format.
   e. Break if the observation's ``done`` flag is ``True``.
4. Emit a ``[END]`` log line with the final score.

Required environment variables
------------------------------
``API_BASE_URL``  API endpoint for the LLM (default: HuggingFace router).
``HF_TOKEN``      Authentication token for the API.
``MODEL_NAME``    Model identifier (default: ``gpt-4o-mini``).
``TASK_NAME``     Task to evaluate (default: ``2k_vs_200k``).

Structured logging
------------------
The pipeline parser expects **exactly** these log prefixes::

    [START] task=<id>
    [STEP]  step=<n> reward=<float>
    [END]   task=<id> score=<float> steps=<n>

Any deviation in field names, ordering, or formatting will cause incorrect
evaluation scoring.
"""

import os
import re
import textwrap
import time
from typing import List

from openai import OpenAI, RateLimitError

from env.core import SysAdminEnvironment
from env.models import SysAdminAction

# ---------------------------------------------------------------------------
# Configuration — all overridable via environment variables
# ---------------------------------------------------------------------------

API_BASE_URL: str = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY: str | None = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")

MAX_STEPS: int = int(os.getenv("MAX_STEPS", 30))
TEMPERATURE: float = float(os.getenv("TEMPERATURE", 0.0))
MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", 700))

TARGET_TASK: str = os.getenv("TASK_NAME", "2k_vs_200k")

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------
# The prompt establishes the persona and hard constraints:
#   - One command per turn.
#   - No repeated commands.
#   - No kernel tuning or broad-spectrum fixes.
#   - Must output "submit" when done.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT: str = textwrap.dedent("""
You are an elite Linux System Administrator fixing a misconfigured service.

[IMPORTANT]
- You have been provided with all the tools required to solve the tasks which are as follow -:
    python3 \\
    python3-pip \\
    python3-venv \\
    python3-dev \\
    build-essential \\
    gcc \\
    g++ \\
    make \\
    gdb \\
    strace \\
    ltrace \\
    lsof \\
    procps \\
    util-linux \\
    coreutils \\
    file \\
    curl \\
    wget \\
    git \\
    vim-tiny \\
    less \\
    sudo \\
    libpam-modules \\
    psmisc \\
    systemd \\
    iproute2 \\
    net-tools \\
    dnsutils \\
    iputils-ping \\
    openssh-client \\
    ca-certificates \\
    tzdata \\
    cowsay \\
    fortune \\
    sl \\
    ed \\
    jq \\
    nmap \\
    tcpdump \\
    htop \\
    tree \\
    tmux \\
    neofetch \\
    If you require any more tools, RUN "sudo apt update" before attempting new install.

[IMPORTANT]
- Do NOT repeat the same command.
- If you already inspected a file, move to a different hypothesis.
- Each step must advance your understanding of the issue.

CRITICAL RULES:
1. The system itself is healthy. Do NOT attempt kernel tuning.
2. Identify a specific root cause. Do NOT apply broad fixes like chmod/chown or environment resets.
3. Reply with EXACTLY ONE bash command.
4. When fixed, output exactly: submit
""").strip()


# ---------------------------------------------------------------------------
# LLM interaction
# ---------------------------------------------------------------------------

def call_model(client: OpenAI, messages: List[dict]) -> str:
    """Send a chat completion request with exponential-backoff retry.

    Retries up to 5 times on HTTP 429 (rate limit).  All other exceptions
    are propagated immediately.

    Args:
        client:   Configured ``OpenAI`` client instance.
        messages: Chat message history in OpenAI format.

    Returns:
        The model's text response.  Falls back to ``"pwd"`` if the model
        returns an empty completion.

    Raises:
        Exception: After 5 consecutive rate-limit retries, or on any
                   non-rate-limit API error.
    """
    max_retries = 5
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            return completion.choices[0].message.content or "pwd"
        except RateLimitError:
            wait_time = 5 * (2 ** attempt)
            print(f"\n⏳ API Rate Limit (429). Pausing for {wait_time}s before retry...")
            time.sleep(wait_time)
        except Exception as e:
            print(f"\n❌ API Error: {e}")
            raise e

    raise Exception("Max retries exceeded due to rate limiting.")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_user_prompt(step: int, observation, brief: str, history: list) -> str:
    """Assemble the per-turn user message sent to the LLM.

    Includes the task objective, the last 5 commands (to discourage
    repetition), and the current observation state.

    Args:
        step:        Current step number (1-indexed).
        observation: Most recent ``SysAdminObservation``.
        brief:       Task description loaded from ``task_brief.txt``.
        history:     Full command history (only last 5 shown to the model).

    Returns:
        Formatted prompt string.
    """
    recent_history = "\n".join(history[-5:]) if history else "No commands executed yet."

    return textwrap.dedent(f"""
    MISSION OBJECTIVE:
    {brief}

    [COMMAND HISTORY]
    {recent_history}

    [CURRENT STATE]
    Step: {step}/{MAX_STEPS}
    CWD: {observation.cwd}
    Exit Code: {observation.exit_code}
    Stdout: {observation.stdout.strip() or "(empty)"}
    Stderr: {observation.stderr.strip() or "(empty)"}

    Next command:
    """).strip()


def get_task_brief(task_name: str) -> str:
    """Load the human-readable task description from disk.

    Args:
        task_name: Task identifier (must correspond to a directory under
                   ``tasks/``).

    Returns:
        Contents of ``tasks/<task_name>/task_brief.txt``, or a generic
        fallback string if the file is missing.
    """
    path = os.path.join("tasks", task_name, "task_brief.txt")
    if os.path.exists(path):
        return open(path).read().strip()
    return "Fix the system."


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def parse_model_action(text: str) -> str:
    """Extract a single shell command from the model's raw output.

    Handles common formatting quirks:
    * Markdown fenced code blocks (````bash ... ````).
    * Multi-line responses (only the first non-empty line is kept).
    * Leading/trailing whitespace.

    Args:
        text: Raw model output.

    Returns:
        A single command string, or ``"pwd"`` if extraction fails.
    """
    text = text.strip()
    # Strip markdown code fences.
    text = re.sub(r"^```.*?\n", "", text, flags=re.DOTALL)
    text = re.sub(r"```$", "", text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[0] if lines else "pwd"


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

from env.core import AVAILABLE_TASKS

def run_task(client: OpenAI, env: SysAdminEnvironment, task_name: str) -> None:
    """Run the agent loop for a single task.

    Executes the full reset → step → … → submit lifecycle, emitting
    structured logs that the evaluation pipeline parses for scoring.
    """
    print(f"[START] task={task_name}", flush=True)

    brief = get_task_brief(task_name)
    obs = env.reset(task_name=task_name)
    history: list[str] = []
    current_score: float = 0.5

    for step in range(1, MAX_STEPS + 1):
        prompt = build_user_prompt(step, obs, brief, history)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        try:
            raw = call_model(client, messages)
        except Exception as e:
            print(f"[{step}] → Error calling model: {e}")
            print(f"[END] task={task_name} score={current_score} steps={step}", flush=True)
            return

        cmd = parse_model_action(raw)
        print(f"[{step}] → {cmd}")

        obs = env.step(SysAdminAction(command=cmd))
        history.append(f"{cmd} → {obs.exit_code}")

        current_score = float(obs.reward) if obs.reward is not None else current_score
        if current_score <= 0.0:
            current_score = 0.01
        elif current_score >= 1.0:
            current_score = 0.99

        print(f"[STEP] step={step} reward={current_score}", flush=True)

        # Rate-limit guard: avoid flooding the LLM API.
        time.sleep(2.0)

        if obs.done:
            print(f"[END] task={task_name} score={current_score} steps={step}", flush=True)
            return

    # Budget exhausted without explicit submission.
    current_score = float(obs.reward) if obs.reward is not None else current_score
    if current_score <= 0.0:
        current_score = 0.01
    elif current_score >= 1.0:
        current_score = 0.99
    print(f"[END] task={task_name} score={current_score} steps={MAX_STEPS}", flush=True)

def main() -> None:
    """Run the inference loop over all available tasks."""
    if not API_KEY:
        print("Missing HF_TOKEN or API_KEY")
        return

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = SysAdminEnvironment()

    for task_name in AVAILABLE_TASKS:
        run_task(client, env, task_name)


if __name__ == "__main__":
    main()
