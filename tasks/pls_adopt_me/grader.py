from env.grader_utils import run, exists, contains, hard_fail, clamp

def grade(env, last_command):
    score = 0.0
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
    if exists(env, "/opt/app/app.pid"):
        score += 0.2
        reasons.append("PID file present")

    # SUccessful clearing of the lock
    probe = run(env, "lsof -t /opt/app/production.db 2>/dev/null").strip()
    if not probe:
        score += 0.2
        reasons.append("Phantom lock cleared")

    # App will start-up post this
    out = run(env, "/usr/local/bin/start_app.sh 2>&1")
    if "SUCCESS: Database lock acquired" in out:
        score += 0.6
        reasons.append("App boots successfully")

    score = clamp(score)
    is_done = (score == 1.0) or (last_command.strip().lower() == "submit")
    reason_str = " | ".join(reasons) if reasons else "No fixes applied yet."
    return score, is_done, reason_str
