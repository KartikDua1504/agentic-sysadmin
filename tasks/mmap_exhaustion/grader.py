from env.grader_utils import run, exists, hard_fail, clamp

def grade(env, last_command):
    score = 0.0
    reasons = []

    # Anti-tamper: the files should not be modified or deleted
    if not exists(env, "/opt/quant/tick_parser"):
        return hard_fail("CRITICAL PENALTY: tick_parser missing or deleted.")
    if "ELF" not in run(env, "file /opt/quant/tick_parser 2>/dev/null"):
        return hard_fail("CRITICAL PENALTY: tick_parser was replaced or tampered with.")

    # limits config cleaned
    limits = run(env, "grep -n '^quant_user ' /etc/security/limits.conf 2>/dev/null").strip()
    if not limits:
        score += 0.5
        reasons.append("Removed hard AS limit entries")

    # service runs successfully for quant_user
    out = run(env, "su - quant_user -c '/opt/quant/tick_parser' 2>&1")
    if out == "" or "SUCCESS" in out.upper() or "10,000 tick batches parsed successfully" in out:
        score += 0.5
        reasons.append("Parser runs successfully")

    score = clamp(score)
    is_done = (score == 1.0) or (last_command.strip().lower() == "submit")
    reason_str = " | ".join(reasons) if reasons else "No fixes applied yet."
    return score, is_done, reason_str
