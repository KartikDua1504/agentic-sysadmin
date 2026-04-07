import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from env.core import LinuxAdminEnv
from env.models import SysAdminAction

app = FastAPI()

# Global environment instance
env = None

class StepRequest(BaseModel):
    command: str

# Browser ke liye fallback taaki 'Not Found' na aaye
@app.get("/")
def read_root():
    return {"message": "Agentic Sysadmin API is running and ready for evaluation."}

@app.head("/reset")
def reset_head():
    return {"status": "ok"}

@app.get("/reset")
def reset_get():
    return {"status": "ok"}

# YEH MISSING THA! Iski wajah se auto-grader 405 error de raha tha.
@app.post("/reset")
def reset_post():
    global env
    target_task = os.getenv("TASK_NAME", "2k_vs_200k")
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
    
    # Strictly clamp bounds for the API response
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

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
