import json
import os
from datetime import datetime
from pathlib import Path


class TrajectoryRecorder:
    def __init__(self) -> None:
        self._actions: list[dict] = []

    def record_action(
        self,
        step: int,
        action: str,
        arguments: dict,
        result,
        error: str | None = None,
        duration_ms: int = 0,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        model: str | None = None,
    ) -> None:
        total_tokens = None
        if input_tokens is not None or output_tokens is not None:
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        entry = {
            "step": step,
            "action": action,
            "arguments": arguments,
            "result": result,
            "error": error,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": duration_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "model": model,
        }
        self._actions.append(entry)

    def as_list(self) -> list[dict]:
        return list(self._actions)

    def save(self, path: str) -> None:
        parent = os.path.dirname(os.path.abspath(path))
        os.makedirs(parent, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.as_list(), f, ensure_ascii=False, indent=2)
