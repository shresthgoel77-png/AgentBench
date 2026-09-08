from constants import TAX_RATE
from invoice import compute_total


def test_compute_total_uses_current_rate():
    assert compute_total(100) == round(100 + 100 * TAX_RATE, 2)


def test_compute_total_zero():
    assert compute_total(0) == 0.0