from env.grader_utils import run, exists, contains, perm_owner, hard_fail
from env.grader_common import BASE_SCORE, add, sub, reason_str, clamp_score

def grade(env, last_command):
    score = BASE_SCORE
    reasons = []

    # Anti-tamper: The files should not be deleted or modified
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

    wrapper_fixed = contains(env, "/usr/local/bin/start-math.sh", "/opt/math_daemon/daemon.py")
    if wrapper_fixed:
        score = add(score, 0.15)
        reasons.append("Fixed wrapper script path")
    else:
        score = sub(score, 0.04)
        reasons.append("Wrapper script path still incorrect")

    _, owner, _ = perm_owner(env, "/var/lib/math_daemon")
    ownership_fixed = (owner == "mathuser")
    if ownership_fixed:
        score = add(score, 0.15)
        reasons.append("Fixed /var/lib/math_daemon ownership")
    else:
        score = sub(score, 0.04)
        reasons.append("/var/lib/math_daemon ownership still incorrect")

    tmpfiles_fixed = contains(env, "/usr/lib/tmpfiles.d/math-daemon.conf", "mathuser mathuser")
    if tmpfiles_fixed:
        score = add(score, 0.20)
        reasons.append("Fixed tmpfiles.d socket permissions")
    else:
        score = sub(score, 0.04)
        reasons.append("tmpfiles.d socket permissions still incorrect")

    boot_output = run(env, "/usr/local/bin/boot_service.sh 2>&1")
    boot_ok = "SUCCESS: Daemon booted" in boot_output
    if boot_ok:
        score = add(score, 0.30)
        reasons.append("Daemon booted successfully")
    else:
        score = sub(score, 0.06)
        reasons.append("Daemon boot still failing")

    score = clamp_score(score)
    is_done = wrapper_fixed and ownership_fixed and tmpfiles_fixed and boot_ok
    if last_command.strip().lower() == "submit":
        is_done = True
    return score, is_done, reason_str(reasons)
