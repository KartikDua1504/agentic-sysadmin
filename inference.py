"""
Inference Script for agentic-sysadmin
===================================
MANDATORY VARIABLES:
    API_BASE_URL  The API endpoint for the LLM.
    MODEL_NAME    The model identifier to use for inference.
    HF_TOKEN      Your Hugging Face / API key.
"""

import os
import re
import textwrap
from openai import OpenAI
from dotenv import load_dotenv

from env.core import LinuxAdminEnv
from env.models import SysAdminAction
from env.registry import TASK_REGISTRY

load_dotenv()
# --- Configuration ---
API_BASE_URL = os.getenv("API_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini") 

MAX_STEPS = int(os.getenv("MAX_STEPS", 30))
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.0))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", 700))

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are an elite Linux System Administrator fixing broken servers.
    
    CRITICAL RULES:
    1. NO REPETITION. If a command fails or yields no useful output, immediately pivot your strategy. 
    2. DO NOT GUESS. Investigate underlying system calls, process limits, file locks, and environmental configurations to find the root cause.
    3. Reply with EXACTLY ONE bash command. No markdown formatting. No explanations.
    4. When you believe the system is fully fixed, output exactly: submit
    """
).strip()

def build_user_prompt(step: int, observation, brief: str, history: list) -> str:
    # Last 5 commands as history so that it does not loop
    recent_history = "\n".join(history[-5:]) if history else "No commands executed yet."

    return textwrap.dedent(
        f"""
        MISSION OBJECTIVE:
        {brief}

        [COMMAND HISTORY - DO NOT REPEAT THESE]
        {recent_history}

        [CURRENT STATE]
        Step: {step}/{MAX_STEPS}
        CWD: {observation.cwd}
        Last Exit Code: {observation.exit_code}
        Stdout: {observation.stdout.strip() if observation.stdout else "(empty)"}
        Stderr: {observation.stderr.strip() if observation.stderr else "(empty)"}

        Provide your next unique bash command:
        """
    ).strip()

# Getting the task_brief.txt to give the problem statement to an AI.
def get_task_brief(task_name: str) -> str:
    """Reads the mission briefing for the agent."""
    brief_path = os.path.join("tasks", task_name, "task_brief.txt")
    if os.path.exists(brief_path):
        with open(brief_path, "r") as f:
            return f.read().strip()
    return "Fix the system and ensure all services are running correctly."


def parse_model_action(response_text: str) -> str:
    # Strip out markdown code blocks if the model ignores the system prompt
    action = response_text.strip()
    action = re.sub(r"^```bash\s*", "", action, flags=re.IGNORECASE)
    action = re.sub(r"^```\s*", "", action)
    action = re.sub(r"\s*```$", "", action)
    
    # Return the first actual line of code
    lines = [line.strip() for line in action.splitlines() if line.strip()]
    return lines[0] if lines else "pwd"

def main():
    if not API_KEY:
        print("-> WARNING: HF_TOKEN or API_KEY is not set!")
        
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    
    # Dictionary to hold the baseline results
    results = {}

    print(f"-> Starting OpenEnv Baseline Evaluation using {MODEL_NAME}")
    print("=" * 50)

    for task_name in TASK_REGISTRY:
        print(f"\n-> Booting Environment: {task_name}")
        env = LinuxAdminEnv(task_name=task_name)
        brief = get_task_brief(task_name)
        
        try:
            obs = env.reset()
            history = []
            
            for step in range(1, MAX_STEPS + 1):
                # Pass both brief and history
                user_prompt = build_user_prompt(step, obs, brief, history)

                try:
                    completion = client.chat.completions.create(
                        model=MODEL_NAME,
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt},
                        ],
                        temperature=TEMPERATURE,
                        max_tokens=MAX_TOKENS,
                    )
                    raw_response = completion.choices[0].message.content or "pwd"
                except Exception as e:
                    print(f"-> API FATAL ERROR: {e}")
                    results[task_name] = 0.0
                    break 

                cmd = parse_model_action(raw_response)
                print(f"   [{step}/{MAX_STEPS}] Agent runs: {cmd}")

                obs, reward, done, info = env.step(SysAdminAction(command=cmd))
                
                # Updating history after execution
                history.append(f"Step {step}: {cmd} -> Exit Code: {obs.exit_code}")

                if done:
                    print(f"-> Task completed by Agent! Score: {reward.score} | Reason: {reward.reasoning}")
                    results[task_name] = reward.score
                    break
            else:
                print(f"-> Max steps reached ({MAX_STEPS}). Final Score: {reward.score}")
                results[task_name] = reward.score 
                
        finally:
            # Always clean up the Docker container before moving to the next task
            try:
                env.container.stop(timeout=1)
                env.container.remove(force=True)
            except:
                pass

    print("\n" + "=" * 50)
    print("-> FINAL BASELINE SCORES")
    print("=" * 50)
    for t, score in results.items():
        print(f" - {t}: {score}/1.0")

if __name__ == "__main__":
    main()
