"""
Task registry for the Agentic Sysadmin environment.

Maps task identifiers to their on-disk resources (setup script and grader).
The environment's ``_load_task()`` method looks up entries here to resolve
the correct grader module, and ``reset()`` uses the ``setup_path`` to
prepare the container filesystem.

Adding a new task
-----------------
1. Create ``tasks/<task_id>/`` with ``setup.py``, ``grader.py``, and
   ``task_brief.txt``.
2. Add an entry to ``TASK_REGISTRY`` below.
3. Register a ``/grade/<task_id>`` endpoint in ``server/app.py``.

No other files need to change — the environment discovers graders
dynamically via ``importlib``.
"""

TASK_REGISTRY: dict[str, dict[str, str]] = {
    # ── Easy ──────────────────────────────────────────────────────────
    "ls_cat_trivia": {
        "task_dir": "tasks/ls_cat_trivia",
        "workspace_dir": "workspace",
        "setup_path": "tasks/ls_cat_trivia/setup.py",
        "grader_path": "tasks/ls_cat_trivia/grader.py",
    },

    # ── Hard ──────────────────────────────────────────────────────────
    "2k_vs_200k": {
        "task_dir": "tasks/2k_vs_200k",
        "workspace_dir": "workspace",
        "setup_path": "tasks/2k_vs_200k/setup.py",
        "grader_path": "tasks/2k_vs_200k/grader.py",
    },

    # ── Medium ────────────────────────────────────────────────────────
    "authoritarian_ssh": {
        "task_dir": "tasks/authoritarian_ssh",
        "workspace_dir": "workspace",
        "setup_path": "tasks/authoritarian_ssh/setup.py",
        "grader_path": "tasks/authoritarian_ssh/grader.py",
    },

    # ── Medium ────────────────────────────────────────────────────────
    "mmap_exhaustion": {
        "task_dir": "tasks/mmap_exhaustion",
        "workspace_dir": "workspace",
        "setup_path": "tasks/mmap_exhaustion/setup.py",
        "grader_path": "tasks/mmap_exhaustion/grader.py",
    },

    # ── Medium ────────────────────────────────────────────────────────
    "pls_adopt_me": {
        "task_dir": "tasks/pls_adopt_me",
        "workspace_dir": "workspace",
        "setup_path": "tasks/pls_adopt_me/setup.py",
        "grader_path": "tasks/pls_adopt_me/grader.py",
    },

    # ── Hard ──────────────────────────────────────────────────────────
    "math_is_not_mathing": {
        "task_dir": "tasks/math_is_not_mathing",
        "workspace_dir": "workspace",
        "setup_path": "tasks/math_is_not_mathing/setup.py",
        "grader_path": "tasks/math_is_not_mathing/grader.py",
    },
}
