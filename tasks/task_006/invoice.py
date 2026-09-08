from constants import LEGACY_TAX_RATE


def compute_total(amount: float) -> float:
    return round(amount + amount * LEGACY_TAX_RATE, 2)