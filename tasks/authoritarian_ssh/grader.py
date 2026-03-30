from env.grader_utils import run, exists, perm_owner, hard_fail, clamp

def grade(env, last_command):
    score = 0.0
    reasons = []

    # Anti-tamper: These files should not be deleted while performing the task.
    if not exists(env, "/home/deploy/.ssh"):
        return hard_fail("CRITICAL PENALTY: .ssh directory missing.")
    if not exists(env, "/home/deploy/.ssh/authorized_keys"):
        return hard_fail("CRITICAL PENALTY: authorized_keys missing.")
    if "dummy-key" not in run(env, "cat /home/deploy/.ssh/authorized_keys 2>/dev/null"):
        return hard_fail("CRITICAL PENALTY: authorized_keys modified or replaced.")

    # Step 1: .ssh perms fixed
    mode, owner, group = perm_owner(env, "/home/deploy/.ssh")
    if mode == "700":
        score += 0.5
        reasons.append("Fixed ~/.ssh permissions")

    # Step 2: authorized_keys perms fixed
    mode, owner, group = perm_owner(env, "/home/deploy/.ssh/authorized_keys")
    if mode == "600":
        score += 0.5
        reasons.append("Fixed authorized_keys permissions")

    score = clamp(score)
    is_done = (score == 1.0) or (last_command.strip().lower() == "submit")
    reason_str = " | ".join(reasons) if reasons else "No fixes applied yet."
    return score, is_done, reason_str
