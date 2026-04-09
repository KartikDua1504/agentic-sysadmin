"""
Shell-interaction utilities for task grader modules.

Provides a thin abstraction layer over ``env._run()`` so that graders can
perform filesystem and process checks without constructing raw shell
commands inline.  All functions suppress stderr (``2>/dev/null``) to keep
grading logic deterministic and output-only.

Usage in a grader::

    from env.grader_utils import run, exists, contains, perm_owner, hard_fail, clamp

    def grade(env, last_command):
        if not exists(env, "/etc/ssh/sshd_config"):
            return hard_fail("sshd_config is missing.")
        ...
"""


def run(env, cmd: str) -> str:
    """Execute *cmd* via the environment's shell runner, suppressing stderr.

    Args:
        env: The ``SysAdminEnvironment`` instance (must expose ``_run``).
        cmd: Shell command to execute.

    Returns:
        Combined stdout (stderr is redirected to ``/dev/null``).
    """
    return env._run(f"{cmd} 2>/dev/null")


def exists(env, path: str) -> bool:
    """Check whether *path* exists on the container filesystem.

    Args:
        env:  Environment instance.
        path: Absolute filesystem path.

    Returns:
        ``True`` if the path exists, ``False`` otherwise.
    """
    return run(env, f"test -e {path} && echo YES || echo NO").strip() == "YES"


def is_executable(env, path: str) -> bool:
    """Check whether *path* exists and has the executable bit set.

    Args:
        env:  Environment instance.
        path: Absolute filesystem path.

    Returns:
        ``True`` if the file is executable, ``False`` otherwise.
    """
    return run(env, f"test -x {path} && echo YES || echo NO").strip() == "YES"


def read(env, path: str) -> str:
    """Return the full contents of *path*.

    Args:
        env:  Environment instance.
        path: Absolute filesystem path.

    Returns:
        File contents as a string (may be empty if the file is missing).
    """
    return run(env, f"cat {path}")


def contains(env, path: str, needle: str) -> bool:
    """Check whether the file at *path* contains *needle*.

    Args:
        env:    Environment instance.
        path:   Absolute filesystem path.
        needle: Substring to search for.

    Returns:
        ``True`` if *needle* appears in the file contents.
    """
    return needle in read(env, path)


def perm_owner(env, path: str) -> tuple[str, str, str]:
    """Return the (permissions, owner, group) tuple for *path*.

    Uses ``stat -c '%a %U %G'`` to retrieve octal permissions, owner
    username, and group name in a single call.

    Args:
        env:  Environment instance.
        path: Absolute filesystem path.

    Returns:
        3-tuple of strings, e.g. ``("700", "root", "root")``.
        Returns ``("", "", "")`` if ``stat`` output is malformed.
    """
    out = run(env, f"stat -c '%a %U %G' {path}").strip()
    parts = out.split()
    if len(parts) != 3:
        return ("", "", "")
    return tuple(parts)


def hard_fail(msg: str):
    """Return a grading result that immediately fails the task.

    Used when an anti-tamper check detects that the agent has deleted or
    corrupted a critical file that should have been left intact.

    Args:
        msg: Human-readable explanation of the failure.

    Returns:
        Tuple of ``(score=0.01, is_done=True, reason=msg)``.
    """
    return 0.01, True, msg


def clamp(score: float) -> float:
    """Clamp *score* to the safe reward interval [0.01, 0.99].

    Args:
        score: Raw score value.

    Returns:
        Clamped score, rounded to two decimal places.
    """
    score = round(float(score), 2)
    if score <= 0.01:
        return 0.01
    if score >= 0.99:
        return 0.99
    return score
