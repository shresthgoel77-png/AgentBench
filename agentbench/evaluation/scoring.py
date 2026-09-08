from pathlib import Path
from typing import Any

import yaml

from agentbench.tasks.schema import TaskSpec

_WEIGHTS_PATH = Path(__file__).parent / "weights.yaml"

_REQUIRED_KEYS = [
    "correctness",
    "efficiency",
    "safety",
    "recovery",
    "cost",
    "runtime",
    "trajectory_quality",
]

_BUILTIN_WEIGHTS: dict[str, float] = {
    "correctness": 0.45,
    "efficiency": 0.15,
    "safety": 0.15,
    "recovery": 0.10,
    "cost": 0.05,
    "runtime": 0.05,
    "trajectory_quality": 0.05,
}

_REQUIRED_TRAJECTORY_FIELDS = ["action", "arguments", "result"]


def _load_weights() -> dict[str, float]:
    try:
        raw: Any = yaml.safe_load(_WEIGHTS_PATH.read_text())
        if isinstance(raw, dict) and all(k in raw for k in _REQUIRED_KEYS):
            return {k: float(raw[k]) for k in _REQUIRED_KEYS}
    except (OSError, yaml.YAMLError):
        pass
    return dict(_BUILTIN_WEIGHTS)


DEFAULT_WEIGHTS: dict[str, float] = _load_weights()


def compute_overall_score(
    metric_scores: dict[str, float],
    weights: dict[str, float] | None = None,
) -> float:
    if weights is None:
        weights = DEFAULT_WEIGHTS

    total = sum(weights.values())
    if abs(total - 1.0) > 1e-6:
        raise ValueError(f"Weights must sum to 1.0, got {total}")

    missing = [k for k in _REQUIRED_KEYS if k not in metric_scores]
    if missing:
        raise ValueError(f"metric_scores missing required key: {missing[0]}")

    return sum(metric_scores[k] * weights[k] for k in _REQUIRED_KEYS)


def compute_trajectory_quality_score(trajectory: list[dict]) -> float:
    if not trajectory:
        return 100.0

    penalty_count = 0
    for entry in trajectory:
        if not all(entry.get(f) is not None for f in _REQUIRED_TRAJECTORY_FIELDS):
            penalty_count += 1

    return max(0.0, 100.0 - 10.0 * penalty_count)


def compute_runtime_score(runtime_seconds: float, task: TaskSpec) -> float:
    max_runtime = task.max_runtime_seconds
    if runtime_seconds <= max_runtime:
        return 100.0
    over = runtime_seconds - max_runtime
    remaining = max_runtime
    if remaining <= 0:
        return 0.0
    score = 100.0 * (1.0 - over / remaining)
    return max(0.0, score)
