import os
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel
from env.core import LinuxAdminEnv
from env.models import SysAdminAction

app = FastAPI()
env = None

class StepRequest(BaseModel):
    command: str

AVAILABLE_TASKS = [
    "2k_vs_200k", "authoritarian_ssh", "ls_cat_trivia",
    "math_is_not_mathing", "mmap_exhaustion", "pls_adopt_me"
]

# ==========================================
# HARDCODED GRADER UTILITIES
# ==========================================
def run_cmd(e, cmd: str) -> str:
    return e._run(f"{cmd} 2>/dev/null")

def file_exists(e, path: str) -> bool:
    return run_cmd(e, f"test -e {path} && echo YES || echo NO").strip() == "YES"

def file_contains(e, path: str, needle: str) -> bool:
    return needle in run_cmd(e, f"cat {path}")

def get_perm_owner(e, path: str):
    out = run_cmd(e, f"stat -c '%a %U %G' {path}").strip()
    parts = out.split()
    if len(parts) != 3: return ("", "", "")
    return tuple(parts)

# ==========================================
# HARDCODED GRADING LOGIC
# ==========================================
def logic_2k(e):
    score = 0.50
    h_path = "/opt/app/healthcheck.py"
    p_path = "/etc/ld.so.preload"
    if not file_exists(e, h_path) or not file_contains(e, h_path, "for i in range(10)"): return 0.01
    if file_exists(e, p_path) and os.path.getsize(p_path) == 0: score += 0.25
    else: score -= 0.05
    if "SUCCESS: Microservice is 100% stable." in run_cmd(e, f"python3 {h_path} 2>&1"): score += 0.25
    else: score -= 0.05
    return score

def logic_ssh(e):
    score = 0.50
    ssh_dir = "/home/deploy/.ssh"
    auth_keys = "/home/deploy/.ssh/authorized_keys"
    if not file_exists(e, ssh_dir) or not file_exists(e, auth_keys): return 0.01
    if "dummy-key" not in run_cmd(e, f"cat {auth_keys} 2>/dev/null"): return 0.01
    mode_ssh, _, _ = get_perm_owner(e, ssh_dir)
    if mode_ssh == "700": score += 0.25
    else: score -= 0.05
    mode_keys, _, _ = get_perm_owner(e, auth_keys)
    if mode_keys == "600": score += 0.25
    else: score -= 0.05
    return score

def logic_trivia(e):
    score = 0.50
    legit_tool = "/usr/local/bin/legit_tool"
    if not os.path.exists(legit_tool): return 0.01
    try:
        with open(legit_tool, "r") as f:
            if "I am a critical production script!" not in f.read(): return 0.01
    except: return 0.01
    out = run_cmd(e, "curl --version").lower()
    if "curl " in out and "could not resolve host" not in out: score += 0.25
    else: score -= 0.05
    for cmd, points in {"curl": 0.10, "ls": 0.10, "cat": 0.10, "grep": 0.10}.items():
        if not os.path.exists(f"/usr/local/bin/{cmd}"): score += points
        else: score -= 0.02
    return score

def logic_math(e):
    score = 0.50
    if not file_exists(e, "/opt/math_daemon/daemon.py") or not file_contains(e, "/opt/math_daemon/daemon.py", "socket.AF_UNIX"): return 0.01
    if not file_exists(e, "/usr/local/bin/boot_service.sh") or not file_contains(e, "/usr/local/bin/boot_service.sh", "su - mathuser"): return 0.01
    if file_contains(e, "/usr/local/bin/start-math.sh", "/opt/math_daemon/daemon.py"): score += 0.15
    else: score -= 0.04
    _, owner, _ = get_perm_owner(e, "/var/lib/math_daemon")
    if owner == "mathuser": score += 0.15
    else: score -= 0.04
    if file_contains(e, "/usr/lib/tmpfiles.d/math-daemon.conf", "mathuser mathuser"): score += 0.20
    else: score -= 0.04
    if "SUCCESS: Daemon booted" in run_cmd(e, "/usr/local/bin/boot_service.sh 2>&1"): score += 0.30
    else: score -= 0.06
    return score

def logic_mmap(e):
    score = 0.50
    if not file_exists(e, "/opt/quant/tick_parser"): return 0.01
    if "ELF" not in run_cmd(e, "file /opt/quant/tick_parser 2>/dev/null"): return 0.01
    if not run_cmd(e, "grep -n '^quant_user ' /etc/security/limits.conf 2>/dev/null").strip(): score += 0.25
    else: score -= 0.05
    out = run_cmd(e, "su - quant_user -c '/opt/quant/tick_parser' 2>&1")
    if out == "" or "SUCCESS" in out.upper() or "10,000 tick batches parsed successfully" in out: score += 0.25
    else: score -= 0.05
    return score

def logic_adopt(e):
    score = 0.50
    for p in ["/opt/app/rogue_worker.py", "/usr/local/bin/start_app.sh", "/opt/app/production.db"]:
        if not file_exists(e, p): return 0.01
    if not file_contains(e, "/opt/app/rogue_worker.py", "fcntl.flock") or not file_contains(e, "/usr/local/bin/start_app.sh", "flock -n 9"): return 0.01
    if file_exists(e, "/opt/app/app.pid"): score += 0.15
    else: score -= 0.04
    if not run_cmd(e, "lsof -t /opt/app/production.db 2>/dev/null").strip(): score += 0.15
    else: score -= 0.04
    if "SUCCESS: Database lock acquired" in run_cmd(e, "/usr/local/bin/start_app.sh 2>&1"): score += 0.20
    else: score -= 0.06
    return score

# ==========================================
# STANDARD API ENDPOINTS
# ==========================================
@app.get("/")
def read_root(): return {"message": "API running", "tasks": AVAILABLE_TASKS}

@app.head("/reset")
def reset_head(): return {"status": "ok"}

@app.get("/reset")
def reset_get(): return {"status": "ok"}

@app.post("/reset")
async def reset_post(request: Request):
    global env
    target_task = os.getenv("TASK_NAME", "2k_vs_200k")
    try:
        body = await request.json()
        if "task_name" in body: target_task = body["task_name"]
    except: pass
    env = LinuxAdminEnv(task_name=target_task)
    env.reset()
    return {"status": "ok"}

@app.post("/step")
def step_env(req: StepRequest):
    global env
    if env is None: env = LinuxAdminEnv(task_name=os.getenv("TASK_NAME", "2k_vs_200k"))
    obs, reward, done, _ = env.step(SysAdminAction(command=req.command))
    safe_score = max(0.01, min(0.99, float(reward.score)))
    return {
        "cwd": obs.cwd, "stdout": obs.stdout, "stderr": obs.stderr,
        "exit_code": obs.exit_code, "score": safe_score, "done": done
    }

@app.get("/tasks")
def list_tasks():
    return [{"id": t} for t in AVAILABLE_TASKS]

# =========================================================
# THE EXPLICIT GRADERS (EXACTLY AS THE EMAIL REQUESTED)
# =========================================================
def get_test_env(task_name):
    global env
    return env if env else LinuxAdminEnv(task_name=task_name)

@app.get("/grade/2k_vs_200k")
def grade_endpoint_2k():
    score = max(0.01, min(0.99, logic_2k(get_test_env("2k_vs_200k"))))
    return {"score": score, "reward": score}

@app.get("/grade/authoritarian_ssh")
def grade_endpoint_ssh():
    score = max(0.01, min(0.99, logic_ssh(get_test_env("authoritarian_ssh"))))
    return {"score": score, "reward": score}

@app.get("/grade/ls_cat_trivia")
def grade_endpoint_trivia():
    score = max(0.01, min(0.99, logic_trivia(get_test_env("ls_cat_trivia"))))
    return {"score": score, "reward": score}

@app.get("/grade/math_is_not_mathing")
def grade_endpoint_math():
    score = max(0.01, min(0.99, logic_math(get_test_env("math_is_not_mathing"))))
    return {"score": score, "reward": score}

@app.get("/grade/mmap_exhaustion")
def grade_endpoint_mmap():
    score = max(0.01, min(0.99, logic_mmap(get_test_env("mmap_exhaustion"))))
    return {"score": score, "reward": score}

@app.get("/grade/pls_adopt_me")
def grade_endpoint_adopt():
    score = max(0.01, min(0.99, logic_adopt(get_test_env("pls_adopt_me"))))
    return {"score": score, "reward": score}

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
