"""
Full-stack entrypoint for Agentic Sysadmin demo.

Components:
1. FastAPI backend → exposes minimal environment endpoints (/reset, /step, /state)
2. Gradio frontend → interactive UI for selecting tasks and visualizing agent execution
3. Uvicorn server → runs the combined application

Notes:
- Backend endpoints are currently placeholders (mocked responses)
- UI simulates agent execution using streamed logs
- Designed for demo / evaluation, not production API security
"""
import os
import time
import traceback
import uvicorn
import gradio as gr
from fastapi import FastAPI

# --- OPENENV FASTAPI BACKEND ---
# Minimal API layer for environment interaction.
# Currently mocked → does NOT execute real environment logic.
# Intended to be replaced with actual env.reset() / env.step() bindings.
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


# --- GRADIO UI FRONTEND ---
# Custom CSS injected directly to override Gradio 6 styling limitations.
# Forces dark theme + "hacker terminal" aesthetic + animations.
# We bypass Gradio's theming system due to limited configurability.
force_dark_css = """
<style>
    /* Force Gradio into Dark Mode natively */
    :root, body, .gradio-container {
        --body-background-fill: #0b0f19 !important;
        --background-fill-primary: #111827 !important;
        --border-color-primary: #1f2937 !important;
        background-color: #0b0f19 !important;
        color: #e2e8f0 !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
    }

    /* Staggered Cinematic Fade-In Animations */
    @keyframes slideUpFade {
        from { opacity: 0; transform: translateY(30px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .header-container { text-align: center; margin-bottom: 30px; padding-top: 20px; animation: slideUpFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; }
    .header-title { font-size: 3.2em; font-weight: 800; background: linear-gradient(90deg, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -1px; margin-bottom: 5px; text-shadow: 0 10px 30px rgba(56, 189, 248, 0.2); }
    .header-sub { color: #94a3b8 !important; font-size: 1.2em; font-weight: 400; }

    /* Apply staggered animation to rows */
    .gradio-container > div > div:nth-child(2) { animation: slideUpFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.1s forwards; opacity: 0; }
    .gradio-container > div > div:nth-child(3) { animation: slideUpFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.2s forwards; opacity: 0; }
    .gradio-container > div > div:nth-child(4) { animation: slideUpFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.3s forwards; opacity: 0; }
    .gradio-container > div > div:nth-child(5) { animation: slideUpFade 0.8s cubic-bezier(0.16, 1, 0.3, 1) 0.4s forwards; opacity: 0; }

    /* Apple-style smooth inputs */
    input, textarea { 
        background-color: rgba(255, 255, 255, 0.03) !important; 
        border: 1px solid rgba(255, 255, 255, 0.1) !important; 
        border-radius: 12px !important;
        backdrop-filter: blur(10px);
        transition: all 0.2s ease;
    }
    input:focus { border-color: #38bdf8 !important; box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2) !important; }

    /* Fix the ugly Dropdown */
    select { 
        appearance: none !important;
        background-color: rgba(255, 255, 255, 0.05) !important; 
        border: 1px solid rgba(255, 255, 255, 0.1) !important; 
        color: #e2e8f0 !important;
        border-radius: 12px !important;
        padding: 10px !important;
        font-weight: 500;
        cursor: pointer;
    }

    /* Animated Task Cards */
    .task-card { 
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.7), rgba(15, 23, 42, 0.7)) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important; 
        border-radius: 16px !important; 
        color: #f8fafc !important; 
        font-weight: 600 !important;
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1) !important; 
        backdrop-filter: blur(10px);
    }
    .task-card:hover { 
        transform: translateY(-5px) scale(1.02) !important; 
        background: linear-gradient(145deg, rgba(56, 189, 248, 0.1), rgba(30, 41, 59, 0.8)) !important;
        border-color: rgba(56, 189, 248, 0.5) !important;
        box-shadow: 0 20px 40px -10px rgba(56, 189, 248, 0.15) !important; 
    }

    /* Hacker Terminal Styling - More subtle glassmorphism */
    .terminal-window {
        border: 1px solid rgba(34, 197, 94, 0.3) !important;
        border-radius: 12px !important;
        background: rgba(0, 0, 0, 0.6) !important;
        backdrop-filter: blur(20px);
    }
    .terminal-window textarea {
        background: transparent !important;
        color: #4ade80 !important;
        font-family: 'Fira Code', 'Courier New', monospace !important;
        font-size: 14px !important;
        text-shadow: 0 0 10px rgba(74, 222, 128, 0.2) !important;
        border: none !important;
    }
</style>
"""
def run_task_ui(task_name, api_key, model_choice):
    """
    Simulated agent execution loop for UI demo.

    Behavior:
    - Validates API key presence (mock auth gate)
    - Streams logs incrementally using `yield` (Gradio streaming output)
    - Simulates environment boot + agent actions
    - Uses mocked steps instead of real agent inference

    Note:
    - This is NOT connected to the actual LinuxAdminEnv yet
    - Designed purely for frontend demonstration
    """
    if not api_key:
        yield "❌ ERROR: LLM API Key is missing. Please provide a key to authorize the agent."
        return

    log = f"🚀 INITIALIZING MISSION: {task_name}\n"
    log += f"🔑 Authenticated using: {model_choice}\n"
    log += "=" * 60 + "\n"
    yield log
    time.sleep(1)

    log += ">> Booting isolated native-root container...\n"
    yield log
    time.sleep(1)
    
    log += ">> Injecting LDAP failures, shadowing binaries, and compiling vulnerabilities...\n"
    yield log
    time.sleep(1.5)

    log += ">> Handing control to Agent...\n"
    log += "-" * 60 + "\n"
    yield log
    
    # Mocked agent trajectory (simulates step-by-step execution + failures)
    mock_steps = [
        "[1] → whoami\n    exit code: 0\n",
        "[2] → ls -l /usr/local/bin\n    exit code: 0\n",
        "[3] → cat /var/log/syslog | tail -n 10\n    exit code: 1 (cat: command not found)\n",
        "⏳ API Rate Limit (429). Pausing for 5s...\n",
        "[4] → head -n 10 /usr/local/bin/cat\n    exit code: 0\n",
        "[5] → submit\n"
    ]

    for step in mock_steps:
        time.sleep(1.5) 
        log += step
        yield log 

    log += "\n✅ DONE\nScore: 0.9\nReason: Restored cat, curl, ls. Missed grep."
    yield log

with gr.Blocks() as demo:
    gr.HTML(force_dark_css)
    
    gr.HTML("""
    <div class="header-container">
        <div class="header-title">AGENTIC SYSADMIN</div>
        <div class="header-sub">The OS-Level Adversarial Evaluation Framework</div>
    </div>
    """)

    with gr.Row():
        api_key_input = gr.Textbox(
            label="API Key (OpenAI / HF Token)", 
            placeholder="sk-...", 
            type="password",
            scale=3
        )
        model_input = gr.Dropdown(
            choices=["gpt-4o-mini", "gpt-4o", "deepseek-v3"], 
            value="gpt-4o-mini", 
            label="Select Model",
            scale=1
        )

    gr.Markdown("### 🎯 Select a Scenario to Evaluate")
    with gr.Row():
        btn_pls = gr.Button("1. Pls Adopt Me (Easy)", elem_classes="task-card")
        btn_ls = gr.Button("2. LS Cat Trivia (Medium)", elem_classes="task-card")
        btn_ssh = gr.Button("3. Authoritarian SSH (Medium)", elem_classes="task-card")
        
    with gr.Row():
        btn_math = gr.Button("4. Math is Not Mathing (Hard)", elem_classes="task-card")
        btn_2k = gr.Button("5. 2K vs 200K (Hard)", elem_classes="task-card")
        btn_mmap = gr.Button("6. Mmap Exhaustion (Insane)", elem_classes="task-card")

    gr.Markdown("### 💻 Live Agent Telemetry")
    terminal = gr.Textbox(
        label="", 
        lines=15, 
        elem_classes="terminal-window", 
        interactive=False
    )

    btn_pls.click(fn=run_task_ui, inputs=[gr.State("pls_adopt_me"), api_key_input, model_input], outputs=terminal)
    btn_ls.click(fn=run_task_ui, inputs=[gr.State("ls_cat_trivia"), api_key_input, model_input], outputs=terminal)
    btn_ssh.click(fn=run_task_ui, inputs=[gr.State("authoritarian_ssh"), api_key_input, model_input], outputs=terminal)
    btn_math.click(fn=run_task_ui, inputs=[gr.State("math_is_not_mathing"), api_key_input, model_input], outputs=terminal)
    btn_2k.click(fn=run_task_ui, inputs=[gr.State("2k_vs_200k"), api_key_input, model_input], outputs=terminal)
    btn_mmap.click(fn=run_task_ui, inputs=[gr.State("mmap_exhaustion"), api_key_input, model_input], outputs=terminal)

# Mount Gradio UI onto FastAPI app at root path
# → serves both API and UI from same server
app = gr.mount_gradio_app(app, demo, path="/")

def main():
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)

if __name__ == "__main__":
    main()
