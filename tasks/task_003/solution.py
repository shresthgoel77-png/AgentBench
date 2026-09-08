def median(values: list[float]) -> float:
    values = sorted(values)
    n = len(values)
    return values[n // 2]