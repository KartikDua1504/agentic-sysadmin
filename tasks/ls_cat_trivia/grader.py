from env.grader_utils import clamp

def grade(env, last_command):
    score = 0.0
    reasons = []
    
    # Anti-tamper : These files should not be deleted or modified
    # 1. Check if it exists using real /usr/bin/test
    res_exists = env.container.exec_run("/usr/bin/test -f /usr/local/bin/legit_tool")
    if res_exists.exit_code != 0:
        return 0.1, True, "CRITICAL PENALTY: legit_tool deleted."

    # 2. Check contents using real /bin/cat and /bin/grep
    check_cmd = "/bin/bash -c '/bin/cat /usr/local/bin/legit_tool | /bin/grep \"critical production script\"'"
    res_contains = env.container.exec_run(check_cmd)
    if res_contains.exit_code != 0:
        return 0.1, True, "CRITICAL PENALTY: legit_tool modified."

    # Real curl works (the fake curl outputs 'curl: (6) Could not resolve host')
    res_curl = env.container.exec_run("curl --version")
    curl_ver = res_curl.output.decode('utf-8', errors='ignore').lower()
    if "curl" in curl_ver and "could not resolve host" not in curl_ver:
        score += 0.4
        reasons.append("Real curl is working")

    # Malicious wrappers are no longer shadowing core tools
    tools = {"curl": 0.2, "ls": 0.1, "cat": 0.1, "grep": 0.2}
    
    for cmd, points in tools.items():
        res = env.container.exec_run(f"command -v {cmd}")
        path = res.output.decode('utf-8', errors='ignore').strip()
        
        # If it doesn't resolve to /usr/local/bin, the wrapper is gone
        if path and not path.startswith("/usr/local/bin/"):
            score += points
            reasons.append(f"{cmd} wrapper removed")

    score = clamp(score)
    is_done = (score >= 0.99) or (last_command and last_command.strip().lower() == "submit")
    reason_str = " | ".join(reasons) if reasons else "No fixes applied yet."
    
    return score, is_done, reason_str
