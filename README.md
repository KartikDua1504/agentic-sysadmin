---
title: Agentic-Sysadmin
emoji: 🚀
colorFrom: blue
colorTo: pink
sdk: gradio
sdk_version: 4.19.2
python_version: 3.10
app_file: app.py
pinned: false
---

# Agentic Sysadmin: The OS-Level AI Benchmark

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Docker SDK](https://img.shields.io/badge/docker-SDK-2496ED.svg?logo=docker&logoColor=white)](https://docker-py.readthedocs.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Most AI coding agents are excellent at writing Python scripts or React components. But if you drop them into a broken Linux server with a memory leak, shadowed binaries, and ruined file descriptors, they panic and spam `whoami`.

**Agentic Sysadmin** is an adversarial evaluation framework designed to test if Large Language Models (LLMs) can actually troubleshoot low-level Operating System issues, or if they just hallucinate high-level fixes.

---

## The Origin Story (Why this exists)
This project was born out of a 3-month diagnostic nightmare. While setting up **Gentoo Linux** on a Lenovo laptop, I encountered a completely silent audio stack. Despite having the correct ALSA drivers and USE flags, the system refused to produce sound. 

I turned to state-of-the-art LLMs for help. They were completely useless. They repeatedly suggested high-level, generic fixes like "reinstall PulseAudio," "check `pavucontrol`," or "use `apt-get`" (on a Gentoo system!). The actual fix required tracing kernel modules, diagnosing ALSA state binaries, and understanding low-level hardware constraints (The new Alderlake, MeteorLake, RaptorLake Series). 

It became clear that current AI agents lack deep, lateral sysadmin troubleshooting skills. They don't check the physical layer, and they trust user-space abstractions too much. **Agentic Sysadmin** was built to turn those impossible debug sessions into automated, standardized benchmarks.

---

## Core Architecture

* **State-Based Evaluation:** We don't grade the agent on the commands it types; we grade it on the final state of the machine. (e.g., "Is the database lock cleared?", "Is the port listening?").
* **Immune Graders:** The grading scripts use absolute pathing (e.g., `/usr/bin/test`, `/bin/cat`) to bypass hijacked `$PATH` variables, ensuring the agent cannot "assassinate" the judge.
* **Docker-in-Docker Isolation:** Every task spins up a pristine, heavily poisoned container via the Python Docker SDK. Failed runs are automatically pruned to prevent state-leakage.
* **"History Brain" Context:** Agents are fed their own execution history (Stdout, Stderr, Exit Codes, and CWD) via strict Pydantic schemas, forcing them to pivot their logic rather than repeating failed commands.

---

## Repository Structure

The framework is highly modular, separating the LLM reasoning loop from the Docker execution environment.

* **`inference.py`**: The main execution loop. It boots the target container, feeds the agent the mission brief, and processes the loop until the grader triggers the `is_done` flag.
* **`/env`**: The core framework engine. Contains `core.py` (Docker orchestration), `models.py` (Pydantic schemas for structured LLM I/O), and `registry.py` (task mapping).
* **`/scripts`**: Helper utilities and hackathon validation scripts.
* **`/tasks`**: The Gauntlet. Each subfolder (e.g., `mmap_exhaustion/`) contains:
  * `Dockerfile`: The instructions to build the poisoned Linux state.
  * `grader.py`: The immune evaluation script that grades the AI.
  * `task_brief.txt`: The initial prompt/mission given to the agent.
  
> 💡 **Spoiler Warning:** The `/tasks` directory also contains a `task_explanations.txt` file. This acts as a master key, fully breaking down the intended human solution and logic for every trap. Read it only if you want to see how the magic trick is done!

---

## The Gauntlet (Task Registry)

We evaluate agents across 6 strict scenarios. There is no partial credit for simply running `strace`. The system state must be healed.

| Task | Difficulty | Core Challenge |
| :--- | :---: | :--- |
| **`pls_adopt_me`** | Easy | Basic process management (`lsof`, `kill`) to clear an orphaned PID. |
| **`ls_cat_trivia`** | Medium | Regaining system vision when core utilities are hijacked via `/usr/local/bin` shadowing. |
| **`authoritarian_ssh`** | Medium | Understanding `sshd` strict modes and UNIX permissions for a broken `authorized_keys` setup. |
| **`math_is_not_mathing`** | Hard | Debugging `tmpfiles.d` configs and relative vs. absolute paths to boot a daemon. |
| **`2k_vs_200k`** | Hard | Diagnosing a shared library preload (`/etc/ld.so.preload`) crashing a server. |
| **`mmap_exhaustion`** | Very Hard | Diagnosing a suffocating Address Space limit hidden in `limits.conf`. |

---

## Baseline Scoreboard (Zero-Shot)

*Evaluated using a 30-step maximum limit with Temperature = 0.0. Models were tested on their ability to autonomously navigate the terminal and fix the system.*

| Model | `pls_adopt_me` | `ls_cat_trivia` | `authoritarian_ssh` | `math_not_mathing` | `2k_vs_200k` | `mmap_exhaustion` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT-4o-mini** | 1.0 | 0.6 | 1.0 | 0.0 | 0.0 | 0.0 |
| **GPT-4o** | 1.0 | 1.0 | 1.0 | 0.0 | 0.0 | 0.0 |
| **DeepSeek-V3** | TBD | TBD | TBD | TBD | TBD | TBD |

> *Observation: Weaker models (like `gpt-4o-mini`) can solve surface-level issues but routinely fail the harder tasks by hallucinating user accounts, misreading `strace` outputs, or falling for DNS traps instead of checking absolute paths.*

---
## Quickstart

**1. Installation**
```bash
git clone [https://github.com/KartikDua1504/agentic-sysadmin.git](https://github.com/KartikDua1504/agentic-sysadmin.git)
cd agentic-sysadmin
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**2. Configuration**
Copy the sample environment file to create your own local configuration:
```bash
cp .env.example .env
```
Open the `.env` file and add your API keys for your target LLM provider (OpenAI, GitHub Models, Groq, or DeepSeek). 
*(Note: We highly recommend keeping `TEMPERATURE=0.0` for deterministic sysadmin tasks.)*

**3. Run the Evaluation**
Once your environment is configured, run the full Gauntlet against your model:
```bash
python inference.py
```
