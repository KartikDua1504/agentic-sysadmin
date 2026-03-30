# grader_utils.py

def run(env, cmd: str) -> str:
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
    out = run(env, f"stat -c '%a %U %G' {path}").strip()
    parts = out.split()
    if len(parts) != 3:
        return ("", "", "")
    return tuple(parts)

def hard_fail(msg: str):
    return 0.1, True, msg

def clamp(score: float) -> float:
    return max(0.0, min(1.0, round(score, 2)))
