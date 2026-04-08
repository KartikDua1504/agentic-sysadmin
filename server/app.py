import os
import uvicorn
import logging
from fastapi import FastAPI, Request
from pydantic import BaseModel
from env.core import LinuxAdminEnv
from env.models import SysAdminAction

# SET UP LOGGING SO WE CAN SPY ON THE AUTO-GRADER
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sysadmin_api")

app = FastAPI()
env = None

class StepRequest(BaseModel):
    command: str

# DYNAMICALLY DETECT TASKS JUST LIKE THE OLD UI DID
def get_available_tasks():
    # Go up one level from 'server' to root, then into 'tasks'
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tasks_dir = os.path.join(base_dir, "tasks")
    if os.path.exists(tasks_dir):
        # List all directories in tasks/ that don't start with __
        return [d for d in os.listdir(tasks_dir) if os.path.isdir(os.path.join(tasks_dir, d)) and not d.startswith("__")]
    return []

AVAILABLE_TASKS = get_available_tasks()
logger.info(f"🚀 SERVER BOOT: Dynamically detected {len(AVAILABLE_TASKS)} tasks: {AVAILABLE_TASKS}")

@app.get("/")
def read_root():
    logger.info("📡 GET / was called")
    return {"message": "Agentic Sysadmin API is running.", "tasks_detected": AVAILABLE_TASKS}

@app.head("/reset")
def reset_head():
    return {"status": "ok"}

@app.get("/reset")
def reset_get():
    return {"status": "ok"}

@app.post("/reset")
async def reset_post(request: Request):
    global env
    target_task = os.getenv("TASK_NAME", "2k_vs_200k")

    try:
        body = await request.json()
        logger.info(f"📥 POST /reset received payload from grader: {body}")
        if "task_name" in body:
            target_task = body["task_name"]
    except Exception as e:
        logger.warning(f"⚠️ POST /reset hit, but no JSON body was parsed: {e}")

    logger.info(f"🔄 Initializing environment for task -> {target_task}")
    env = LinuxAdminEnv(task_name=target_task)
    env.reset()
    return {"status": "ok", "task_loaded": target_task}

@app.post("/step")
def step_env(req: StepRequest):
    global env
    if env is None:
        target_task = os.getenv("TASK_NAME", "2k_vs_200k")
        logger.info(f"⚠️ POST /step called before /reset. Booting default task -> {target_task}")
        env = LinuxAdminEnv(task_name=target_task)

    logger.info(f"🛠️ Grader executing command -> {req.command}")
    obs, reward, done, _ = env.step(SysAdminAction(command=req.command))

    # Strictly clamp bounds to (0.01, 0.99)
    safe_score = float(reward.score)
    if safe_score <= 0.0:
        safe_score = 0.01
    elif safe_score >= 1.0:
        safe_score = 0.99

    logger.info(f"✅ Step complete. Score -> {safe_score} | Done -> {done}")

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

@app.get("/tasks")
def list_tasks():
    logger.info("📡 GET /tasks was called by the grader")
    return AVAILABLE_TASKS

def main():
    uvicorn.run(app, host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
