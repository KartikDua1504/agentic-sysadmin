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

@app.get("/")
def read_root():
    return {"message": "Agentic Sysadmin API is running and ready for evaluation."}

@app.head("/reset")
def reset_head():
    return {"status": "ok"}

@app.get("/reset")
def reset_get():
    return {"status": "ok"}

# FIX: Now properly reads the requested task_name from the Auto-Grader's JSON
@app.post("/reset")
async def reset_post(request: Request):
    global env
    target_task = os.getenv("TASK_NAME", "2k_vs_200k")
    
    try:
        body = await request.json()
        if "task_name" in body:
            target_task = body["task_name"]
    except Exception:
        pass # Fallback to env var if body is empty or invalid

    env = LinuxAdminEnv(task_name=target_task)
    env.reset()
    return {"status": "ok"}

@app.post("/step")
def step_env(req: StepRequest):
    global env
    if env is None:
        target_task = os.getenv("TASK_NAME", "2k_vs_200k")
        env = LinuxAdminEnv(task_name=target_task)

    obs, reward, done, _ = env.step(SysAdminAction(command=req.command))
    
    # Strictly clamp bounds to (0.01, 0.99)
    safe_score = float(reward.score)
    if safe_score <= 0.0:
        safe_score = 0.01
    elif safe_score >= 1.0:
        safe_score = 0.99

    return {
        "cwd": obs.cwd,
        "stdout": obs.stdout,
        "stderr": obs.stderr,
        "exit_code": obs.exit_code,
        "score": safe_score,
        "done": done,
    }

@app.get("/state")
def get_state():
    return {"status": "ok"}

# FIX: Expose the list of tasks directly to the Auto-Grader
@app.get("/tasks")
def list_tasks():
    return [
        "2k_vs_200k",
        "authoritarian_ssh",
        "ls_cat_trivia",
        "math_is_not_mathing",
        "mmap_exhaustion",
        "pls_adopt_me"
    ]

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
