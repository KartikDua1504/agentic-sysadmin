"""
Shared scoring primitives used by task grader modules.

Every grader in ``tasks/<task_id>/grader.py`` imports from this module to
ensure consistent score clamping, rounding, and formatting across all tasks.

Constants
---------
``BASE_SCORE`` (0.50)
    Default score before any checks are applied.  Graders start here and
    add/subtract based on which conditions pass or fail.

``MIN_SCORE`` / ``MAX_SCORE`` (0.01 / 0.99)
    Hard floor and ceiling.  Prevents degenerate edge cases in the
    evaluation pipeline (e.g. division by zero in normalisation, or a
    perfect 1.0 that leaves no headroom for improvement signals).

``ROUND_DP`` (4)
    Decimal places to round to after clamping.
"""

from __future__ import annotations

from typing import List

# -- Scoring constants -----------------------------------------------------

BASE_SCORE: float = 0.50
MIN_SCORE: float = 0.01
MAX_SCORE: float = 0.99
ROUND_DP: int = 4


# -- Arithmetic helpers ----------------------------------------------------

def clamp_score(score: float) -> float:
    """Clamp *score* to [MIN_SCORE, MAX_SCORE] and round.

    Args:
        score: Raw score value (may exceed bounds).

    Returns:
        Clamped and rounded score.
    """
    score = float(score)
    if score < MIN_SCORE:
        score = MIN_SCORE
    elif score > MAX_SCORE:
        score = MAX_SCORE
    return round(score, ROUND_DP)


def add(score: float, delta: float) -> float:
    """Add *delta* to *score* and clamp the result.

    Use this instead of raw ``+`` to guarantee bounds invariants.
    """
    return clamp_score(score + delta)


def sub(score: float, delta: float) -> float:
    """Subtract *delta* from *score* and clamp the result.

    Use this instead of raw ``-`` to guarantee bounds invariants.
    """
    return clamp_score(score - delta)


def reason_str(reasons: List[str]) -> str:
    """Join a list of grader observations into a single summary string.

    Args:
        reasons: List of human-readable check outcomes (e.g.
                 ``"Fixed ~/.ssh permissions"``).

    Returns:
        Pipe-delimited string, or a default message if *reasons* is empty.
    """
    return " | ".join(reasons) if reasons else "No fixes applied yet."
