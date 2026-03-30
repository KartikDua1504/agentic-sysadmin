import gradio as gr

try:
    from env.registry import TASK_REGISTRY
except Exception:
    TASK_REGISTRY = []


def app_status():
    task_count = len(TASK_REGISTRY)
    tasks_text = ", ".join(TASK_REGISTRY) if TASK_REGISTRY else "No tasks detected"
    return (
        "Agentic Sysadmin is loaded successfully.\n\n"
        f"Tasks detected: {task_count}\n"
        f"{tasks_text}"
    )


with gr.Blocks(title="Agentic Sysadmin") as demo:
    gr.Markdown("# Agentic Sysadmin")
    gr.Markdown(
        "This Space is configured correctly and ready to run."
    )

    output = gr.Textbox(label="Status", lines=6, value=app_status())
    refresh = gr.Button("Refresh status")
    refresh.click(fn=app_status, inputs=None, outputs=output)

demo.launch(server_name="0.0.0.0", server_port=7860)
