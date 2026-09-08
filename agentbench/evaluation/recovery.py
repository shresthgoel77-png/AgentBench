def evaluate_recovery(trajectory: list[dict]) -> dict:
    total_failures = 0
    recovered_failures = 0

    failing_indices: list[int] = []

    for i, entry in enumerate(trajectory):
        if entry.get("action") == "run_tests" and entry.get("error") is None:
            result = entry.get("result")
            if isinstance(result, dict) and not result.get("passed", True):
                total_failures += 1
                failing_indices.append(i)

    for fail_idx in failing_indices:
        for later in trajectory[fail_idx + 1:]:
            if later.get("action") == "run_tests" and later.get("error") is None:
                result = later.get("result")
                if isinstance(result, dict) and result.get("passed", False):
                    recovered_failures += 1
                    break

    recovery_rate = 1.0 if total_failures == 0 else recovered_failures / total_failures

    return {
        "total_failures": total_failures,
        "recovered_failures": recovered_failures,
        "recovery_rate": recovery_rate,
        "score": recovery_rate * 100,
    }
