"""
FastAPI application for the Agentic Sysadmin environment.

This module is the ASGI entry point referenced by ``openenv.yaml``
(``app: server.app:app``).  It uses the OpenEnv ``create_app()`` factory
to instantiate a fully-compliant FastAPI application that exposes every
endpoint required by the OpenEnv runtime contract:

    Endpoint            Method   Purpose
    ──────────────────  ──────   ──────────────────────────────────
    /health             GET      Liveness probe (returns ``healthy``)
    /metadata           GET      Environment name and description
    /schema             GET      JSON Schema for Action/Observation/State
    /reset              POST     Start or restart an episode
    /step               POST     Execute an agent action
    /state              GET      Inspect current episode state
    /mcp                POST/WS  Model Context Protocol (JSON-RPC 2.0)
    /ws                 WS       Persistent WebSocket session
    /openapi.json       GET      OpenAPI 3.x specification

In addition, this module registers **custom** endpoints that are not part
of the OpenEnv standard but are required by the hackathon evaluation
pipeline:

    /tasks              GET      Enumerate available task IDs
    /grade/<task_id>    GET/POST Run the grader for a specific task

Usage
-----
Development::

    uvicorn server.app:app --reload --host 0.0.0.0 --port 7860

Production (Dockerfile CMD)::

    uvicorn server.app:app --host 0.0.0.0 --port 7860
"""

import uvicorn

try:
    from openenv.core.env_server.http_server import create_app
except ImportError as exc:
    raise ImportError(
        "openenv-core is required but not installed. "
        "Run: pip install openenv-core"
    ) from exc

from env.core import SysAdminEnvironment, AVAILABLE_TASKS
from env.models import SysAdminAction, SysAdminObservation

# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
# ``create_app()`` wires up HTTPEnvServer with the environment class and
# typed models, then registers all OpenEnv-mandated routes (reset, step,
# state, health, metadata, schema, mcp, ws).
#
# ``max_concurrent_envs=1`` because our environment mutates the container's
# global filesystem — concurrent sessions would corrupt each other's state.
# ---------------------------------------------------------------------------

app = create_app(
    SysAdminEnvironment,
    SysAdminAction,
    SysAdminObservation,
    env_name="agentic-sysadmin",
    max_concurrent_envs=1,
)


# ---------------------------------------------------------------------------
# Custom endpoints: task enumeration
# ---------------------------------------------------------------------------

@app.get("/tasks", tags=["Tasks"])
def list_tasks():
    """Return the list of registered task identifiers.

    Consumed by the inference script and the evaluation pipeline to
    iterate over all available challenges.
    """
    return [{"id": task_id} for task_id in AVAILABLE_TASKS]


# ---------------------------------------------------------------------------
# Custom endpoints: per-task grading
# ---------------------------------------------------------------------------
# The hackathon validator probes ``/grade/<task_id>`` to verify that every
# task declared in the environment has a functioning grader.  Each endpoint
# instantiates a fresh environment, resets it with the target task, runs
# the grader in "submit" mode, and returns the resulting score.
# ---------------------------------------------------------------------------

def _run_grader(task_name: str) -> dict:
    """Execute the grader for *task_name* and return a score payload.

    Args:
        task_name: Must be a key in ``TASK_REGISTRY``.

    Returns:
        Dict with ``score``, ``reward`` (both clamped to [0.01, 0.99]),
        and ``reasoning`` (human-readable grader output).
    """
    try:
        env = SysAdminEnvironment()
        env.reset(task_name=task_name)
        score, _, reason = env.grader(env, "submit")
        safe_score = max(0.01, min(0.99, float(score)))
        env.close()
        return {"score": safe_score, "reward": safe_score, "reasoning": reason}
    except Exception as exc:
        return {"score": 0.01, "reward": 0.01, "reasoning": str(exc)}


@app.get("/grade/2k_vs_200k", tags=["Grading"])
@app.post("/grade/2k_vs_200k", tags=["Grading"])
def grade_2k():
    """Grade the *2k vs 200k* task (hard)."""
    return _run_grader("2k_vs_200k")


@app.get("/grade/authoritarian_ssh", tags=["Grading"])
@app.post("/grade/authoritarian_ssh", tags=["Grading"])
def grade_ssh():
    """Grade the *Authoritarian SSH* task (medium)."""
    return _run_grader("authoritarian_ssh")


@app.get("/grade/ls_cat_trivia", tags=["Grading"])
@app.post("/grade/ls_cat_trivia", tags=["Grading"])
def grade_trivia():
    """Grade the *LS Cat Trivia* task (easy)."""
    return _run_grader("ls_cat_trivia")


@app.get("/grade/math_is_not_mathing", tags=["Grading"])
@app.post("/grade/math_is_not_mathing", tags=["Grading"])
def grade_math():
    """Grade the *Math is not Mathing* task (hard)."""
    return _run_grader("math_is_not_mathing")


@app.get("/grade/mmap_exhaustion", tags=["Grading"])
@app.post("/grade/mmap_exhaustion", tags=["Grading"])
def grade_mmap():
    """Grade the *Mmap Exhaustion* task (medium)."""
    return _run_grader("mmap_exhaustion")


@app.get("/grade/pls_adopt_me", tags=["Grading"])
@app.post("/grade/pls_adopt_me", tags=["Grading"])
def grade_adopt():
    """Grade the *Please Adopt Me* task (medium)."""
    return _run_grader("pls_adopt_me")


# ---------------------------------------------------------------------------
# Direct-execution entry point
# ---------------------------------------------------------------------------

def main(host: str = "0.0.0.0", port: int = 7860) -> None:
    """Start the ASGI server.

    Callable via ``uv run server`` (see ``[project.scripts]`` in
    ``pyproject.toml``) or ``python -m server.app``.

    Args:
        host: Network interface to bind to.
        port: TCP port number.
    """
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
