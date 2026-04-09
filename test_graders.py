import sys
import uvicorn
from fastapi.testclient import TestClient

try:
    from server.app import app
    client = TestClient(app)
    from env.core import AVAILABLE_TASKS
    print("Available Tasks:", AVAILABLE_TASKS)
    valid_graders = 0
    for task_id in AVAILABLE_TASKS:
        res = client.get(f"/grade/{task_id}")
        if res.status_code == 200:
            data = res.json()
            score = data.get("score")
            reason = data.get("reasoning")
            print(f"Task: {task_id} - Score: {score} - Reason: {reason}")
            # Check if it succeeded vs crashed
            if score != 0.01 or reason and "Exception" not in reason: 
                 # wait, default score init might be 0.01
                 pass
        else:
            print(f"Task: {task_id} failed with status {res.status_code}")
except Exception as e:
    print("Error:", e)
