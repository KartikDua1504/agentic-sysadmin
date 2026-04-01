"""
Inference Script (OpenEnv Hackathon Compliant)
"""

import os
import re
import textwrap
import time
from typing import List

from openai import OpenAI, RateLimitError

from env.core import LinuxAdminEnv
from env.models import SysAdminAction

# ==========================================
# MANDATORY OPENENV VARIABLES
# ==========================================
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
- Do NOT repeat the same command.
- If you already inspected a file, move to a different hypothesis.
- Each step must advance your understanding of the issue.

CRITICAL RULES:
1. The system itself is healthy. Do NOT attempt kernel tuning, system limits, or environment exports.
2. Focus on inspecting files and configurations inside /etc, /opt, and /usr/local.
3. Identify a specific root cause. Do NOT apply broad fixes like chmod/chown or environment resets.
4. Reply with EXACTLY ONE bash command.
5. When fixed, output exactly: submit
""").strip()


def call_model(client: OpenAI, messages: List[dict]) -> str:
    """Calls the LLM using the official OpenAI client with Exponential Backoff."""
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
    path = os.path.join("tasks", task_name, "task_brief.txt")
    if os.path.exists(path):
        return open(path).read().strip()
    return "Fix the system."


def parse_model_action(text):
    text = text.strip()
    text = re.sub(r"^```.*?\n", "", text, flags=re.DOTALL)
    text = re.sub(r"```$", "", text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    return lines[0] if lines else "pwd"


def main():
    if not API_KEY:
        print("❌ Missing HF_TOKEN or API_KEY")
        return

    print(f"\n🚀 Running task: {TARGET_TASK} against {API_BASE_URL} using {MODEL_NAME}")
    print("=" * 60)

    # Initialize the mandatory OpenAI client
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    env = LinuxAdminEnv(task_name=TARGET_TASK)
    brief = get_task_brief(TARGET_TASK)

    obs = env.reset()
    history = []

    for step in range(1, MAX_STEPS + 1):
        prompt = build_user_prompt(step, obs, brief, history)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        raw = call_model(client, messages)
        cmd = parse_model_action(raw)

        print(f"[{step}] → {cmd}")

        obs, reward, done, _ = env.step(SysAdminAction(command=cmd))
        history.append(f"{cmd} → {obs.exit_code}")
        
        # Slight delay to prevent immediate 429s on fast inferences
        time.sleep(2.0)

        if done:
            print("\n✅ DONE")
            print(f"Score: {reward.score}")
            print(f"Reason: {reward.reasoning}")
            return

    print("\n⚠️ Max steps reached")
    print(f"Final Score: {reward.score}")


if __name__ == "__main__":
    main()
