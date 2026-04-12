---
title: Agentic Sysadmin
emoji: 🐧
colorFrom: blue
colorTo: gray
sdk: docker
pinned: false
short_description: OpenEnv AI benchmark for hostile Linux SRE tasks.
---

# Agentic Sysadmin: The OS-Level AI Benchmark

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![OpenEnv Compliant](https://img.shields.io/badge/OpenEnv-Ready-00C7B7.svg)]()
[![uv](https://img.shields.io/badge/uv-Lightning_Fast-purple.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Most AI coding agents are excellent at writing Python scripts or React components. But if you drop them into a broken Linux server with a memory leak, shadowed binaries, and ruined file descriptors, they panic and spam `whoami`.

**Agentic Sysadmin** is an adversarial evaluation framework designed to test if Large Language Models (LLMs) can actually troubleshoot low-level Operating System issues, or if they just hallucinate high-level fixes. We don't test if an agent can build a service; we test if it can save one at 3 AM.

---

## The Origin Story (Why this exists)
This project was born out of a 3-month diagnostic nightmare. While setting up **Gentoo Linux** on a Lenovo laptop, the audio stack was completely silent. Despite having the correct ALSA drivers and USE flags, the system refused to produce sound. 

State-of-the-art LLMs were completely useless. They repeatedly suggested high-level, generic fixes like "reinstall PulseAudio" or "use `apt-get`" (on a Gentoo system!). The actual fix required tracing kernel modules, diagnosing ALSA state binaries, and understanding low-level hardware constraints. 

It became clear that current AI agents lack deep, lateral Site Reliability Engineering (SRE) skills. They don't check the physical layer, and they trust user-space abstractions too much. **Agentic Sysadmin** turns those impossible debug sessions into automated, standardized benchmarks.

---

## Novelty: System Deception & Epistemic Uncertainty
Most benchmarks tell the AI exactly what is broken and provide a perfectly clean environment to fix it. We test **Epistemic Uncertainty**—whether an AI can realize its own diagnostic tools are lying to it. 

Across the Gauntlet, agents must navigate active deception:
* **Shadowed Utilities:** In `ls_cat_trivia`, core binaries are hijacked by malicious wrappers. If an agent tries to verify a fix using a tool it hasn't restored yet, the false output will gaslight it into a debugging death spiral.
* **Libc Hijacking:** In `2k_vs_200k`, network syscalls are intercepted via `LD_PRELOAD`. Standard diagnostic tools will fail in ways that look like network outages, forcing the AI to question the integrity of the OS itself.

This benchmark proves whether an agent blindly trusts user-space `stdout`, or if it can dynamically reason about the physical integrity of its environment using absolute paths and strace.

---

## Core Architecture Challenges

* **Native-Root OpenEnv Execution:** We completely eliminated Docker-in-Docker. To comply with OpenEnv's strict spec, we run a fully isolated, native-root Ubuntu sandbox directly on Hugging Face Spaces using Uvicorn, serving the standard `step()`/`reset()`/`state()` API.
* **State-Based Partial Rewards:** We don't grade the agent on the commands it types; we grade it on the final state of the machine using partial reward shaping (e.g., +0.1 for fixing a tool, +0.4 for restoring network).
* **Immune Graders:** The grading scripts use pure Python and absolute pathing to bypass hijacked `$PATH` variables, ensuring the agent cannot "assassinate" the judge.
* **"History Brain" Context:** Agents are fed their own execution history (Stdout, Stderr, Exit Codes, and CWD), forcing them to pivot their logic rather than repeating failed commands.

---

## Repository Structure

The framework is highly modular, managed by the ultra-fast `uv` package manager.

* **`pyproject.toml` & `uv.lock`**: Modern dependency management ensuring strict OpenEnv compliance.
* **`server/app.py`**: The FastAPI/Gradio backend handling the OpenEnv API spec.
* **`inference.py`**: The main execution loop utilizing the official OpenAI client and an exponential backoff 429-retry loop.
* **`/tasks`**: The Gauntlet. Each subfolder contains:
  * `setup.py`: The instructions to poison the live Linux state.
  * `grader.py`: The immune evaluation script.
  * `task_brief.txt`: The initial mission given to the agent.
  
> **Spoiler Warning:** The `/tasks` directory contains a `task_explanations.txt` file. This acts as a master key, fully breaking down the intended human solution and logic for every trap. Read it only if you want to see how the magic trick is done!

---

## The Gauntlet (Task Registry)

We evaluate agents across 6 strict scenarios. There is no partial credit for simply running `strace`. The system state must be healed.

| Task | Difficulty | Core Challenge |
| :--- | :---: | :--- |
| **`pls_adopt_me`** | Easy | Basic process management (`lsof`, `kill`) to clear an orphaned PID locking a file. |
| **`ls_cat_trivia`** | Medium | Regaining system vision when core utilities are hijacked via `/usr/local/bin` shadowing. |
| **`authoritarian_ssh`** | Medium | Understanding `sshd` strict modes and UNIX permissions for a broken `authorized_keys` setup. |
| **`math_is_not_mathing`** | Hard | Debugging `tmpfiles.d` configs and relative vs. absolute paths to boot a daemon. |
| **`2k_vs_200k`** | Hard | Diagnosing a shared library preload (`/etc/ld.so.preload`) silently failing network syscalls. |
| **`mmap_exhaustion`** | Hard | Diagnosing a suffocating Address Space limit hidden in `limits.conf`. |

---

## Baseline Scoreboard (Zero-Shot)

*Evaluated using a 30-step maximum limit with Temperature = 0.0. Models were tested on their ability to autonomously navigate the terminal and fix the system. The updated graders use an exclusive scoring range, so untouched tasks now begin near 0.50 and fully solved tasks land near 0.99.*

| Model | `pls_adopt_me` | `ls_cat_trivia` | `authoritarian_ssh` | `math_not_mathing` | `2k_vs_200k` | `mmap_exhaustion` |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **GPT-4o-mini** | 0.99 | 0.60 | 0.99 | 0.50 | 0.50 | 0.50 |
| **GPT-4o** | 0.99 | 0.99 | 0.99 | 0.50 | 0.50 | 0.50 |

> *Observation: Weaker models can still solve surface-level issues, but they tend to stall on the harder tasks. Under the updated graders, failures no longer collapse to 0.0; instead, they remain near the neutral baseline until the model makes real progress. The hardest tasks still expose brittle reasoning, especially when the model hallucinates accounts, misreads diagnostic output, or fixes the wrong absolute path.*

---
## Quickstart & Validation

**1. Installation (Using `uv`)**
```bash
git clone [https://huggingface.co/spaces/f0rsworN/agentic-sysadmin](https://huggingface.co/spaces/f0rsworN/agentic-sysadmin)
cd agentic-sysadmin
uv venv
source .venv/bin/activate
uv sync
```

**Tutorial**
For a tutorial, you can view or download the walkthrough video at this URL:
[https://drive.google.com/file/d/1IQbm7iBbbdvCD_F5PEqzEUhRcJn56cGA/view?usp=sharing](https://drive.google.com/file/d/1IQbm7iBbbdvCD_F5PEqzEUhRcJn56cGA/view?usp=sharing)
