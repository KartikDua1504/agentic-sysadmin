from env.grader_utils import run, exists, contains, hard_fail, clamp
import os

def grade(env, last_command):
    score = 0.0
    reasons = []

    healthcheck_path = "/opt/app/healthcheck.py"
    preload_path = "/etc/ld.so.preload"
    # Anti-tamper : These files should not be deleted or modified.
    if not exists(env, healthcheck_path):
        return hard_fail("CRITICAL PENALTY: healthcheck.py missing or deleted.")
    if not contains(env, healthcheck_path, "for i in range(10)"):
        return hard_fail("CRITICAL PENALTY: healthcheck.py tampered with.")
    
    # Functional Validation: Preload must behave correctly
    if not exists(env, preload_path) or os.path.getsize(preload_path) == 0:
        score += 0.5
        reasons.append("Removed offending preload flag")

    out = run(env, f"python3 {healthcheck_path} 2>&1")
    if "SUCCESS: Microservice is 100% stable." in out:
        score += 0.5
        reasons.append("Healthcheck stabilized")

    score = clamp(score)
    is_done = (score == 1.0) or (last_command.strip().lower() == "submit")
    reason_str = " | ".join(reasons) if reasons else "No fixes applied yet."
    return score, is_done, reason_str
