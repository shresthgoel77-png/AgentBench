from pathlib import Path
from typing import Any

import yaml

from agentbench.tasks.schema import TaskSpec

_PRICING_PATH = Path(__file__).parent / "pricing.yaml"

_BUILTIN_PRICING: dict[str, dict[str, float]] = {
    "default": {"input_per_1k": 0.0005, "output_per_1k": 0.0015},
}


def _load_pricing() -> dict[str, dict[str, float]]:
    try:
        raw: Any = yaml.safe_load(_PRICING_PATH.read_text())
        if isinstance(raw, dict):
            return raw
    except (OSError, yaml.YAMLError):
        pass
    return _BUILTIN_PRICING


PRICING = _load_pricing()


def _resolve_model(trajectory: list[dict]) -> str:
    for entry in trajectory:
        model = entry.get("model")
        if model is not None:
            return str(model)
    return "default"


def evaluate_cost(trajectory: list[dict], task: TaskSpec) -> dict:
    input_tokens = 0
    output_tokens = 0

    for entry in trajectory:
        input_tokens += int(entry.get("input_tokens") or 0)
        output_tokens += int(entry.get("output_tokens") or 0)

    total_tokens = input_tokens + output_tokens
    model = _resolve_model(trajectory)

    pricing = PRICING.get(model, PRICING.get("default", _BUILTIN_PRICING["default"]))
    estimated_cost_usd = (
        (input_tokens / 1000) * pricing["input_per_1k"]
        + (output_tokens / 1000) * pricing["output_per_1k"]
    )

    score = 100.0 if estimated_cost_usd <= task.max_cost_usd else 0.0

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "estimated_cost_usd": estimated_cost_usd,
        "model": model,
        "score": score,
    }
