import uvicorn
import gradio as gr
from fastapi import FastAPI
import traceback

try:
    from env.registry import TASK_REGISTRY
    debug_log = "Registry imported successfully."
except Exception as e:
    TASK_REGISTRY = []
    debug_log = f"CRITICAL ERROR loading registry:\n{traceback.format_exc()}"

app = FastAPI()

@app.get("/reset")
@app.post("/reset")
def reset_env():
    return {"status": "success", "message": "Environment reset"}

@app.post("/step")
def step_env():
    return {"status": "success", "message": "Step executed"}

@app.get("/state")
def get_state():
    return {"status": "success", "message": "State retrieved"}

def app_status():
    task_count = len(TASK_REGISTRY)
    try:
        tasks_text = ", ".join([str(t) for t in TASK_REGISTRY]) if TASK_REGISTRY else "No tasks loaded"
    except Exception:
        tasks_text = "Tasks loaded, but could not be parsed as text."
        
    return (
        "Agentic Sysadmin Initialization Status:\n\n"
        f"Tasks detected: {task_count}\n"
        f"{tasks_text}\n\n"
        "================ DEBUG LOG ================\n"
        f"{debug_log}"
    )

with gr.Blocks(title="Agentic Sysadmin") as demo:
    gr.Markdown("# Agentic Sysadmin")
    output = gr.Textbox(label="System Status & Logs", lines=12, value=app_status())
    refresh = gr.Button("Refresh status")
    refresh.click(fn=app_status, inputs=None, outputs=output)

app = gr.mount_gradio_app(app, demo, path="/")

def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
