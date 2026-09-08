import pytest

from duration import to_seconds


def test_seconds_only():
    assert to_seconds("90s") == 90


def test_minutes_only():
    assert to_seconds("2m") == 120


def test_hours_only():
    assert to_seconds("2h") == 7200


def test_compound_no_space():
    assert to_seconds("1h30m") == 5400


def test_compound_with_space():
    assert to_seconds("1h 30m") == 5400


def test_compound_minutes_and_seconds():
    assert to_seconds("30m45s") == 1845


def test_invalid_raises():
    with pytest.raises(ValueError):
        to_seconds("nope")