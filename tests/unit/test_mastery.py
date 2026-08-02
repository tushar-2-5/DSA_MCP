import pytest
from memory.mastery import decayed_mastery, update_base_score


def test_decayed_mastery_half_life():
    # 14 days should halve 0.8 to 0.4
    result = decayed_mastery(0.8, 14.0, half_life_days=14.0)
    assert result == pytest.approx(0.4, rel=1e-2)


def test_decayed_mastery_zero_days():
    # Day 0 should have no decay
    result = decayed_mastery(0.8, 0.0)
    assert result == 0.8


def test_update_base_score_pass_optimal():
    result = update_base_score(0.5, "pass", complexity_optimal=True)
    assert result == 0.65


def test_update_base_score_clamp_max():
    # 0.95 + 0.15 = 1.10 -> clamped to 1.0
    result = update_base_score(0.95, "pass", complexity_optimal=True)
    assert result == 1.0


def test_update_base_score_clamp_min():
    # 0.05 - 0.10 = -0.05 -> clamped to 0.0
    result = update_base_score(0.05, "fail")
    assert result == 0.0
