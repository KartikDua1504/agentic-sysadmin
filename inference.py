#!/usr/bin/env python3
"""
LLM-driven inference loop for Agentic Sysadmin tasks.

Flow:
1. Initialize environment (LinuxAdminEnv)
2. Build prompt from current system state
3. Query LLM for next shell command
4. Execute command in environment
5. Repeat until task completion or step limit

Key constraints:
- Model outputs exactly one bash command per step
- Environment provides reward + termination signal
- Loop enforces step budget and basic rate limiting

Designed for OpenEnv-style evaluation (deterministic, step-based).
"""

import os
import re
import textwrap
import time
from typing import List

from openai import OpenAI, RateLimitError

from env.core import LinuxAdminEnv
from env.models import SysAdminAction

# OPENENV VARIABLES
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

MAX_STEPS = int(os.getenv("MAX_STEPS", 30))
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.0))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 700))

TARGET_TASK = os.getenv("TASK_NAME", "2k_vs_200k")

SYSTEM_PROMPT = textwrap.dedent("""
You are an elite Linux System Administrator fixing a misconfigured service.

[IMPORTANT]
- You have been provided with all the tools required to solve the tasks which are as follow -:
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    gcc \
    g++ \
    make \
    gdb \
    strace \
    ltrace \
    lsof \
    procps \
    util-linux \
    coreutils \
    file \
    curl \
    wget \
    git \
    vim-tiny \
    less \
    sudo \
    libpam-modules \
    psmisc \
    systemd \
    iproute2 \
    net-tools \
    dnsutils \
    iputils-ping \
    openssh-client \
    ca-certificates \
    tzdata \
    cowsay \
    fortune \
    sl \
    ed \
    jq \
    nmap \
    tcpdump \
    htop \
    tree \
    tmux \
    neofetch \
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


def call_model(client: OpenAI, messages: List[dict]) -> str:
    """
    Invoke LLM with exponential backoff for rate limits.

    Behavior:
    - Retries on HTTP 429 (RateLimitError) with exponential delay
    - Fails fast on other exceptions
    - Returns raw model output (fallback: "pwd" if empty)

    Guarantees:
    - Always returns a string command
    - Never silently suppresses non-rate-limit errors
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


def build_user_prompt(step, observation, brief, history):
    """
    Construct user prompt for the LLM.

    Includes:
    - Task objective (brief)
    - Recent command history (last 5 steps)
    - Current system state (cwd, stdout, stderr, exit code)

    Purpose:
    - Ground the model in environment state
    - Prevent repeated actions via history exposure
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


def get_task_brief(task_name):
    """
    Load task description from disk.

    Fallback:
        Returns generic instruction if brief file is missing.
    """
    path = os.path.join("tasks", task_name, "task_brief.txt")
    if os.path.exists(path):
        return open(path).read().strip()
    return "Fix the system."


def parse_model_action(text):
    """
    Extract a single shell command from model output.

    Handles:
    - Markdown code blocks (```bash ... ```)
    - Multi-line responses (takes first non-empty line)

    Ensures:
    - Output is always a single command string
    """
    text = text.strip()
    text = re.sub(r"^```.*?\n", "", text, flags=re.DOTALL)
    text = re.sub(r"```$", "", text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[0] if lines else "pwd"

def main():
    """
    Entry point for running a single task with LLM agent.
    """
    if not API_KEY:
        print("Missing HF_TOKEN or API_KEY")
        return

    print("START") 

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    env = LinuxAdminEnv(task_name=TARGET_TASK)
    brief = get_task_brief(TARGET_TASK)

    obs = env.reset()
    history = []

    for step in range(1, MAX_STEPS + 1):
        print("STEP") 
        
        prompt = build_user_prompt(step, obs, brief, history)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        # WRAPPED IN TRY/EXCEPT FOR PHASE 2 COMPLIANCE
        try:
            raw = call_model(client, messages)
        except Exception as e:
            print(f"[{step}] → Error calling model: {e}")
            print("END")
            print("Score: 0.0")
            print("Reason: Model API failure.")
            return

        cmd = parse_model_action(raw)

        # Custom Logging
        print(f"[{step}] → {cmd}")

        obs, reward, done, _ = env.step(SysAdminAction(command=cmd))
        history.append(f"{cmd} → {obs.exit_code}")

        time.sleep(2.0)

        if done:
            print("END") 
            print(f"Score: {reward.score}")
            print(f"Reason: {reward.reasoning}")
            return

    print("END") 
    print(f"Final Score: {reward.score}")

if __name__ == "__main__":
    main()
