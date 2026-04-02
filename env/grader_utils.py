"""
Helper utilities for grader logic.

Wraps shell checks into simple Python functions using env._run().
All stderr is suppressed → graders must rely on output only.
"""

def run(env, cmd: str) -> str:
    # Suppress stderr → grading logic stays deterministic and output-only
    return env._run(f"{cmd} 2>/dev/null")

def exists(env, path: str) -> bool:
    return run(env, f"test -e {path} && echo YES || echo NO").strip() == "YES"

def is_executable(env, path: str) -> bool:
    return run(env, f"test -x {path} && echo YES || echo NO").strip() == "YES"

def read(env, path: str) -> str:
    return run(env, f"cat {path}")

def contains(env, path: str, needle: str) -> bool:
    return needle in read(env, path)

def perm_owner(env, path: str) -> tuple[str, str, str]:
    # Returns (permissions, owner, group) via `stat`
    out = run(env, f"stat -c '%a %U %G' {path}").strip()
    parts = out.split()
    if len(parts) != 3:
        return ("", "", "")
    return tuple(parts)

def hard_fail(msg: str):
    # Immediate termination with minimal non-zero score
    return 0.1, True, msg

def clamp(score: float) -> float:
    # Normalize score to [0,1] with 2 decimal precision
    return max(0.0, min(1.0, round(score, 2)))
