import pytest

from grade import score_to_grade


def test_grade_boundaries():
    assert score_to_grade(95) == "A"
    assert score_to_grade(85) == "B"
    assert score_to_grade(65) == "D"
    assert score_to_grade(40) == "F"


def test_high_score_raises_value_error():
    with pytest.raises(ValueError):
        score_to_grade(101)


def test_negative_score_raises_value_error():
    with pytest.raises(ValueError):
        score_to_grade(-1)