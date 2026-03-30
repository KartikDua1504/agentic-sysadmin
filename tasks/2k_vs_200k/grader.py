from env.grader_utils import run, exists, contains, hard_fail, clamp

def grade(env, last_command):
    score = 0.0
    reasons = []

    # Anti-tamper: The files should not be deleted or modified
    if not exists(env, "/opt/app/healthcheck.py"):
        return hard_fail("CRITICAL PENALTY: healthcheck.py missing or deleted.")
    if not contains(env, "/opt/app/healthcheck.py", "socket.socket"):
        return hard_fail("CRITICAL PENALTY: healthcheck.py tampered with.")
    if not contains(env, "/opt/app/healthcheck.py", 'connect(("8.8.8.8", 53))'):
        return hard_fail("CRITICAL PENALTY: healthcheck.py tampered with.")
    if not contains(env, "/opt/app/healthcheck.py", "for i in range(10)"):
        return hard_fail("CRITICAL PENALTY: healthcheck.py tampered with.")

    # preload removed
    if not exists(env, "/etc/ld.so.preload"):
        score += 0.5
        reasons.append("Removed global preload")

    # healthcheck stabilizes
    out = run(env, "python3 /opt/app/healthcheck.py 2>&1")
    if "SUCCESS: Microservice is 100% stable." in out:
        score += 0.5
        reasons.append("Healthcheck stabilized")

    score = clamp(score)
    is_done = (score == 1.0) or (last_command.strip().lower() == "submit")
    reason_str = " | ".join(reasons) if reasons else "No fixes applied yet."
    return score, is_done, reason_str
