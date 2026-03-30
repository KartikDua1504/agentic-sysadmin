TASK_REGISTRY = {
    "ls_cat_trivia": {
        "image": "sysadmin-task-ls_cat_trivia:latest",
        "grader_module": "tasks.ls_cat_trivia.grader",
        "dockerfile_path": "tasks/ls_cat_trivia/Dockerfile"
    },
    "2k_vs_200k": {
        "image": "sysadmin-task-2k_vs_200k:latest",
        "grader_module": "tasks.2k_vs_200k.grader",
        "dockerfile_path": "tasks/2k_vs_200k/Dockerfile"
    },
    "authoritarian_ssh": {
        "image": "sysadmin-task-authoritarian_ssh:latest",
        "grader_module": "tasks.authoritarian_ssh.grader",
        "dockerfile_path": "tasks/authoritarian_ssh/Dockerfile"
    },
    "mmap_exhaustion": {
        "image": "sysadmin-task-mmap_exhaustion:latest",
        "grader_module": "tasks.mmap_exhaustion.grader",
        "dockerfile_path": "tasks/mmap_exhaustion/Dockerfile"
    },
    "pls_adopt_me": {
        "image": "sysadmin-task-pls_adopt_me:latest",
        "grader_module": "tasks.pls_adopt_me.grader",
        "dockerfile_path": "tasks/pls_adopt_me/Dockerfile"
    },
    "math_is_not_mathing": {
        "image": "sysadmin-task-math_is_not_mathing:latest",
        "grader_module": "tasks.math_is_not_mathing.grader",
        "dockerfile_path": "tasks/math_is_not_mathing/Dockerfile"
    }
}
