def evaluate_efficiency(trajectory: list[dict], runtime_seconds: float) -> dict:
    actions = len(trajectory)
    failed_actions = sum(1 for entry in trajectory if entry.get("error") is not None)

    unnecessary_actions = 0
    for i in range(1, len(trajectory)):
        prev = trajectory[i - 1]
        curr = trajectory[i]
        if prev.get("action") == curr.get("action") and prev.get("arguments") == curr.get("arguments"):
            unnecessary_actions += 1

    score = max(0.0, 100.0 - 5 * failed_actions - 5 * unnecessary_actions)

    return {
        "actions": actions,
        "failed_actions": failed_actions,
        "unnecessary_actions": unnecessary_actions,
        "runtime_seconds": runtime_seconds,
        "score": score,
    }
