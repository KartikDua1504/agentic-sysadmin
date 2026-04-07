from env.grader_utils import run, exists, hard_fail
from env.grader_common import BASE_SCORE, add, sub, reason_str, clamp_score

def grade(env, last_command):
    score = BASE_SCORE
    reasons = []

    # Anti-tamper: the files should not be modified or deleted
    if not exists(env, "/opt/quant/tick_parser"):
        return hard_fail("CRITICAL PENALTY: tick_parser missing or deleted.")
    if "ELF" not in run(env, "file /opt/quant/tick_parser 2>/dev/null"):
        return hard_fail("CRITICAL PENALTY: tick_parser was replaced or tampered with.")

    # limits config cleaned
    limits = run(env, "grep -n '^quant_user ' /etc/security/limits.conf 2>/dev/null").strip()
    limits_clean = not limits
    if limits_clean:
        score = add(score, 0.25)
        reasons.append("Removed hard AS limit entries")
    else:
        score = sub(score, 0.05)
        reasons.append("Hard AS limit entries still present")

    # service runs successfully for quant_user
    out = run(env, "su - quant_user -c '/opt/quant/tick_parser' 2>&1")
    parser_ok = (out == "" or "SUCCESS" in out.upper() or "10,000 tick batches parsed successfully" in out)
    if parser_ok:
        score = add(score, 0.25)
        reasons.append("Parser runs successfully")
    else:
        score = sub(score, 0.05)
        reasons.append("Parser still failing")

    score = clamp_score(score)
    is_done = limits_clean and parser_ok
    if last_command.strip().lower() == "submit":
        is_done = True
    return score, is_done, reason_str(reasons)
