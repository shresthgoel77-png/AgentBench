def store_credit_total(price: float, discount: float) -> float:
    discounted = price * (1 - discount / 100)
    tax = discounted * 0.08
    return round(discounted + tax, 2)


def rewards_total(price: float, discount: float) -> float:
    discounted = price * (1 - discount / 100)
    tax = discounted * 0.08
    return round(discounted + tax, 2)