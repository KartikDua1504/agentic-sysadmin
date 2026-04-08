import os
import uvicorn
import importlib
import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
from env.core import LinuxAdminEnv
from env.models import SysAdminAction

logger = logging.getLogger("sysadmin_api")
app = FastAPI()
env = None

class StepRequest(BaseModel):
    command: str

AVAILABLE_TASKS = [
    "2k_vs_200k", "authoritarian_ssh", "ls_cat_trivia",
    "math_is_not_mathing", "mmap_exhaustion", "pls_adopt_me"
]

@app.get("/")
def read_root():
    return {"message": "API running", "tasks": AVAILABLE_TASKS}

@app.post("/reset")
async def reset_post(request: Request):
    global env
    target_task = os.getenv("TASK_NAME", "2k_vs_200k")
    try:
        body = await request.json()
        if "task_name" in body:
            target_task = body["task_name"]
    except:
        pass
    env = LinuxAdminEnv(task_name=target_task)
    env.reset()
    return {"status": "ok", "task_loaded": target_task}

@app.post("/step")
def step_env(req: StepRequest):
    global env
    if env is None:
        env = LinuxAdminEnv(task_name=os.getenv("TASK_NAME", "2k_vs_200k"))
    obs, reward, done, _ = env.step(SysAdminAction(command=req.command))
    safe_score = max(0.01, min(0.99, float(reward.score)))
    return {
        "cwd": obs.cwd,
        "stdout": obs.stdout,
        "stderr": obs.stderr,
        "exit_code": obs.exit_code,
        "score": safe_score,
        "done": done
    }

@app.get("/tasks")
def list_tasks():
    return [{"id": t} for t in AVAILABLE_TASKS]

# =========================================================
# THE EXPLICIT DUMB GRADERS (EXACTLY MATCHING THE EMAIL)
# =========================================================
def _grade_task(task_name: str):
    global env
    try:
        # Gracefully handle if the grader pings this without hitting /reset first
        test_env = env
        if test_env is None:
            test_env = LinuxAdminEnv(task_name=task_name)
        
        grader_module = importlib.import_module(f"tasks.{task_name}.grader")
        raw_score, _, _ = grader_module.grade(test_env, "")
        
        score = max(0.01, min(0.99, float(raw_score)))
        
        # STRICT SCHEMA: ONLY RETURN SCORE AND REWARD. NO EXTRA KEYS.
        return {"score": score, "reward": score}
    except Exception as e:
        logger.error(f"Grader error: {e}")
        # STRICT SCHEMA ON ERROR: NEVER RETURN AN ERROR KEY.
        return {"score": 0.01, "reward": 0.01}

# Explicitly defining each route so the auto-grader can't possibly miss them
@app.get("/grade/2k_vs_200k")
def grade_2k(): return _grade_task("2k_vs_200k")

@app.get("/grade/authoritarian_ssh")
def grade_ssh(): return _grade_task("authoritarian_ssh")

@app.get("/grade/ls_cat_trivia")
def grade_trivia(): return _grade_task("ls_cat_trivia")

@app.get("/grade/math_is_not_mathing")
def grade_math(): return _grade_task("math_is_not_mathing")

@app.get("/grade/mmap_exhaustion")
def grade_mmap(): return _grade_task("mmap_exhaustion")

@app.get("/grade/pls_adopt_me")
def grade_adopt(): return _grade_task("pls_adopt_me")

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
