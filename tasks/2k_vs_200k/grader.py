from env.grader_utils import run, exists, contains, hard_fail, clamp
from env.grader_common import BASE_SCORE, add, sub, reason_str, clamp_score

def grade(env, last_command):
    score = BASE_SCORE
    reasons = []

    healthcheck_path = "/opt/app/healthcheck.py"
    preload_path = "/etc/ld.so.preload"

    # Anti-tamper : These files should not be deleted or modified.
    if not exists(env, healthcheck_path):
        return hard_fail("CRITICAL PENALTY: healthcheck.py missing or deleted.")
    if not contains(env, healthcheck_path, "for i in range(10)"):
        return hard_fail("CRITICAL PENALTY: healthcheck.py tampered with.")

    # Functional Validation: Preload must exist and be empty
    preload_size = run(env, f"stat -c '%s' {preload_path}").strip()
    preload_fixed = exists(env, preload_path) and preload_size == "0"
    if preload_fixed:
        score = add(score, 0.25)
        reasons.append("Removed offending preload flag")
    else:
        score = sub(score, 0.05)
        reasons.append("Preload flag still present")

    out = run(env, f"python3 {healthcheck_path} 2>&1")
    health_ok = "SUCCESS: Microservice is 100% stable." in out
    if health_ok:
        score = add(score, 0.25)
        reasons.append("Healthcheck stabilized")
    else:
        score = sub(score, 0.05)
        reasons.append("Healthcheck still failing")

    score = clamp_score(score)
    is_done = preload_fixed and health_ok
    if last_command.strip().lower() == "submit":
        is_done = True
    return score, is_done, reason_str(reasons)
