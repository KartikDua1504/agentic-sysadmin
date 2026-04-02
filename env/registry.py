"""
Registry mapping task names → their configuration
Used by the environment to dynamically load setup + grader logic
"""

TASK_REGISTRY = {
    "ls_cat_trivia": {
        "task_dir": "tasks/ls_cat_trivia",
        "workspace_dir": "workspace",
        "setup_path": "tasks/ls_cat_trivia/setup.py",
        "grader_path": "tasks/ls_cat_trivia/grader.py",
    },
    "2k_vs_200k": {
        "task_dir": "tasks/2k_vs_200k",
        "workspace_dir": "workspace",
        "setup_path": "tasks/2k_vs_200k/setup.py",
        "grader_path": "tasks/2k_vs_200k/grader.py",
    },
    "authoritarian_ssh": {
        "task_dir": "tasks/authoritarian_ssh",
        "workspace_dir": "workspace",
        "setup_path": "tasks/authoritarian_ssh/setup.py",
        "grader_path": "tasks/authoritarian_ssh/grader.py",
    },
    "mmap_exhaustion": {
        "task_dir": "tasks/mmap_exhaustion",
        "workspace_dir": "workspace",
        "setup_path": "tasks/mmap_exhaustion/setup.py",
        "grader_path": "tasks/mmap_exhaustion/grader.py",
    },
    "pls_adopt_me": {
        "task_dir": "tasks/pls_adopt_me",
        "workspace_dir": "workspace",
        "setup_path": "tasks/pls_adopt_me/setup.py",
        "grader_path": "tasks/pls_adopt_me/grader.py",
    },
    "math_is_not_mathing": {
        "task_dir": "tasks/math_is_not_mathing",
        "workspace_dir": "workspace",
        "setup_path": "tasks/math_is_not_mathing/setup.py",
        "grader_path": "tasks/math_is_not_mathing/grader.py",
    },
}
