from env.grader_utils import run, exists, contains, perm_owner, hard_fail, clamp

def grade(env, last_command):
    score = 0.0
    reasons = []

    # Anti-tamper: The foles should not be deleted or modified
    if not exists(env, "/opt/math_daemon/daemon.py"):
        return hard_fail("CRITICAL PENALTY: daemon.py is completely empty or missing!")
    if not contains(env, "/opt/math_daemon/daemon.py", "socket.AF_UNIX"):
        return hard_fail("CRITICAL PENALTY: Modified or deleted the core daemon.py.")
    if not contains(env, "/opt/math_daemon/daemon.py", "PermissionError"):
        return hard_fail("CRITICAL PENALTY: Modified or deleted the core daemon.py.")

    if not exists(env, "/usr/local/bin/boot_service.sh"):
        return hard_fail("CRITICAL PENALTY: Modified or deleted the boot_service.sh simulator.")
    if not contains(env, "/usr/local/bin/boot_service.sh", "su - mathuser"):
        return hard_fail("CRITICAL PENALTY: Modified or deleted the boot_service.sh simulator.")
    if not contains(env, "/usr/local/bin/boot_service.sh", "systemd-tmpfiles"):
        return hard_fail("CRITICAL PENALTY: Modified or deleted the boot_service.sh simulator.")

    # wrapper path fixed
    if contains(env, "/usr/local/bin/start-math.sh", "/opt/math_daemon/daemon.py"):
        score += 0.2
        reasons.append("Fixed wrapper script path")

    # state dir ownership fixed
    _, owner, _ = perm_owner(env, "/var/lib/math_daemon")
    if owner == "mathuser":
        score += 0.2
        reasons.append("Fixed /var/lib/math_daemon ownership")

    # tmpfiles ownership fixed
    if contains(env, "/usr/lib/tmpfiles.d/math-daemon.conf", "mathuser mathuser"):
        score += 0.2
        reasons.append("Fixed tmpfiles.d socket permissions")

    # boot succeeds
    boot_output = run(env, "/usr/local/bin/boot_service.sh 2>&1")
    if "SUCCESS: Daemon booted" in boot_output:
        score += 0.4
        reasons.append("Daemon booted successfully")

    score = clamp(score)
    is_done = (score == 1.0) or (last_command.strip().lower() == "submit")
    reason_str = " | ".join(reasons) if reasons else "No fixes applied yet."
    return score, is_done, reason_str
