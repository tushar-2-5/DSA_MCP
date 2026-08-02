import math


def decayed_mastery(
    base_score: float,
    days_since_last_practiced: float,
    half_life_days: float = 14.0,
) -> float:
    """Apply exponential decay: mastery = base_score * exp(-λ * days),
    where λ = ln(2) / half_life_days. Clamp result to [0.0, 1.0].
    """
    if days_since_last_practiced <= 0:
        decayed = base_score
    else:
        lam = math.log(2) / half_life_days
        decayed = base_score * math.exp(-lam * days_since_last_practiced)

    clamped = max(0.0, min(1.0, decayed))
    return round(clamped, 4)


def update_base_score(
    prev_base_score: float, outcome: str, complexity_optimal: bool = False
) -> float:
    """Update base mastery score based on attempt outcome.

    pass + optimal complexity: +0.15
    pass (not optimal): +0.08
    partial: +0.02
    fail: -0.10
    Clamp result to [0.0, 1.0].
    """
    outcome_lower = outcome.lower()
    if outcome_lower == "pass":
        delta = 0.15 if complexity_optimal else 0.08
    elif outcome_lower == "partial":
        delta = 0.02
    elif outcome_lower == "fail":
        delta = -0.10
    else:
        delta = 0.0

    new_score = prev_base_score + delta
    clamped_score = max(0.0, min(1.0, new_score))
    return round(clamped_score, 4)
