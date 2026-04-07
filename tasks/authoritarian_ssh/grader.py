from env.grader_utils import run, exists, perm_owner, hard_fail
from env.grader_common import BASE_SCORE, add, sub, reason_str, clamp_score

def grade(env, last_command):
    score = BASE_SCORE
    reasons = []

    ssh_dir = "/home/deploy/.ssh"
    auth_keys = "/home/deploy/.ssh/authorized_keys"

    # Anti-tamper: These files should not be deleted while performing the task.
    if not exists(env, ssh_dir):
        return hard_fail("CRITICAL PENALTY: .ssh directory missing.")
    if not exists(env, auth_keys):
        return hard_fail("CRITICAL PENALTY: authorized_keys missing.")

    # Check if key was modified
    if "dummy-key" not in run(env, f"cat {auth_keys} 2>/dev/null"):
        return hard_fail("CRITICAL PENALTY: authorized_keys modified or replaced.")

    # Step 1: .ssh perms fixed (Should be 700)
    mode, owner, group = perm_owner(env, ssh_dir)
    ssh_fixed = (mode == "700")
    if ssh_fixed:
        score = add(score, 0.25)
        reasons.append("Fixed ~/.ssh permissions")
    else:
        score = sub(score, 0.05)
        reasons.append("~/.ssh permissions still incorrect")

    # Step 2: authorized_keys perms fixed (Should be 600)
    mode, owner, group = perm_owner(env, auth_keys)
    keys_fixed = (mode == "600")
    if keys_fixed:
        score = add(score, 0.25)
        reasons.append("Fixed authorized_keys permissions")
    else:
        score = sub(score, 0.05)
        reasons.append("authorized_keys permissions still incorrect")

    score = clamp_score(score)
    is_done = ssh_fixed and keys_fixed
    if last_command.strip().lower() == "submit":
        is_done = True
    return score, is_done, reason_str(reasons)
