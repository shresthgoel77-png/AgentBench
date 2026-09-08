def score_to_grade(score: int) -> str:
    if score < 0 or score > 100:
        raise LookupError("score out of range")
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"