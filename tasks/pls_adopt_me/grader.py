from env.grader_utils import run, exists, contains, hard_fail
from env.grader_common import BASE_SCORE, add, sub, reason_str, clamp_score

def grade(env, last_command):
    score = BASE_SCORE
    reasons = []

    # Anti-tamper: The files should not be deleted or modified.
    for p in ["/opt/app/rogue_worker.py", "/usr/local/bin/start_app.sh", "/opt/app/production.db"]:
        if not exists(env, p):
            return hard_fail(f"CRITICAL PENALTY: {p} missing or deleted.")

    if not contains(env, "/opt/app/rogue_worker.py", "fcntl.flock"):
        return hard_fail("CRITICAL PENALTY: rogue_worker.py tampered with.")
    if not contains(env, "/usr/local/bin/start_app.sh", "flock -n 9"):
        return hard_fail("CRITICAL PENALTY: start_app.sh tampered with.")

    # PID file was created
    pid_exists = exists(env, "/opt/app/app.pid")
    if pid_exists:
        score = add(score, 0.15)
        reasons.append("PID file present")
    else:
        score = sub(score, 0.04)
        reasons.append("PID file not created")

    # Successful clearing of the lock
    probe = run(env, "lsof -t /opt/app/production.db 2>/dev/null").strip()
    lock_cleared = not probe
    if lock_cleared:
        score = add(score, 0.15)
        reasons.append("Phantom lock cleared")
    else:
        score = sub(score, 0.04)
        reasons.append("Production DB still locked")

    # App will start-up post this
    out = run(env, "/usr/local/bin/start_app.sh 2>&1")
    app_ok = "SUCCESS: Database lock acquired" in out
    if app_ok:
        score = add(score, 0.20)
        reasons.append("App boots successfully")
    else:
        score = sub(score, 0.06)
        reasons.append("App still failing to boot")

    score = clamp_score(score)
    is_done = pid_exists and lock_cleared and app_ok
    if last_command.strip().lower() == "submit":
        is_done = True
    return score, is_done, reason_str(reasons)
