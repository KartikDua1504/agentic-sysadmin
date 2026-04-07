from fastapi import FastAPI
from pydantic import BaseModel

from env.core import LinuxAdminEnv
from env.models import SysAdminAction

app = FastAPI()

env = None


class StepRequest(BaseModel):
    command: str


@app.post("/reset")
def reset_env(task_name: str = "pls_adopt_me"):
    global env
    env = LinuxAdminEnv(task_name=task_name)
    obs = env.reset()

    return {
        "cwd": obs.cwd,
        "stdout": obs.stdout,
        "stderr": obs.stderr,
        "exit_code": obs.exit_code,
    }


@app.post("/step")
def step_env(req: StepRequest):
    global env

    obs, reward, done, _ = env.step(
        SysAdminAction(command=req.command)
    )

    return {
        "cwd": obs.cwd,
        "stdout": obs.stdout,
        "stderr": obs.stderr,
        "exit_code": obs.exit_code,
        "score": reward.score,
        "done": done,
    }


@app.get("/state")
def get_state():
    return {"status": "ok"}

def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
