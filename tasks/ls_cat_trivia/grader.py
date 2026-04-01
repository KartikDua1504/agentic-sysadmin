from env.grader_utils import run, hard_fail, clamp
import os

def grade(env, last_command):
    score = 0.0
    reasons = []

    legit_tool = "/usr/local/bin/legit_tool"

    # Anti-tamper: Use pure Python to bypass the broken bash environment
    if not os.path.exists(legit_tool):
        return hard_fail("CRITICAL PENALTY: legit_tool deleted.")

    try:
        with open(legit_tool, "r") as f:
            content = f.read()
            if "I am a critical production script!" not in content:
                return hard_fail("CRITICAL PENALTY: legit_tool modified.")
    except Exception:
        return hard_fail("CRITICAL PENALTY: legit_tool unreadable.")

    # Real curl works (the fake curl outputs 'curl: (6) Could not resolve host')
    out = run(env, "curl --version").lower()
    if "curl " in out and "could not resolve host" not in out:
        score += 0.4
        reasons.append("Real curl is working")

    # Malicious wrappers are no longer shadowing core tools
    tools = {"curl": 0.2, "ls": 0.1, "cat": 0.1, "grep": 0.2}

    for cmd, points in tools.items():
        malicious_path = f"/usr/local/bin/{cmd}"
        if not os.path.exists(malicious_path):
            score += points
            reasons.append(f"{cmd} wrapper removed")

    score = clamp(score)
    is_done = (score >= 0.99) or (last_command.strip().lower() == "submit")
    reason_str = " | ".join(reasons) if reasons else "No fixes applied yet."

    return score, is_done, reason_str
