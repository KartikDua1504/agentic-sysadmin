from __future__ import annotations

from typing import List, Tuple

BASE_SCORE = 0.50
MIN_SCORE = 0.01
MAX_SCORE = 0.99
ROUND_DP = 4


def clamp_score(score: float) -> float:
    score = float(score)
    if score < MIN_SCORE:
        score = MIN_SCORE
    elif score > MAX_SCORE:
        score = MAX_SCORE
    return round(score, ROUND_DP)


def add(score: float, delta: float) -> float:
    return clamp_score(score + delta)


def sub(score: float, delta: float) -> float:
    return clamp_score(score - delta)


def reason_str(reasons: List[str]) -> str:
    return " | ".join(reasons) if reasons else "No fixes applied yet."
