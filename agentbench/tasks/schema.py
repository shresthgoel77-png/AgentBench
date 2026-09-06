from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskSpec:
    id: str
    name: str
    description: str
    test_command: str
    readable: list[str]
    writable: list[str]
    max_steps: int
    max_runtime_seconds: int
    max_cost_usd: float
    task_dir: str = field(default="")

    @classmethod
    def from_dict(cls, data: dict) -> "TaskSpec":
        id_ = _require(data, "id", cls.__name__, "id")
        name = _require(data, "name", cls.__name__, "name")
        description = _require(data, "description", cls.__name__, "description")

        tests = _require_mapping(data, "tests", cls.__name__)
        test_command = _require(tests, "command", cls.__name__, "tests.command")

        permissions = _require_mapping(data, "permissions", cls.__name__)
        readable = list(permissions.get("readable", []))
        writable = list(permissions.get("writable", []))

        limits = _require_mapping(data, "limits", cls.__name__)
        max_steps = _require(limits, "max_steps", cls.__name__, "limits.max_steps")
        max_runtime_seconds = _require(
            limits, "max_runtime_seconds", cls.__name__, "limits.max_runtime_seconds"
        )
        max_cost_usd = _require(limits, "max_cost_usd", cls.__name__, "limits.max_cost_usd")

        return cls(
            id=id_,
            name=name,
            description=description,
            test_command=test_command,
            readable=readable,
            writable=writable,
            max_steps=max_steps,
            max_runtime_seconds=max_runtime_seconds,
            max_cost_usd=max_cost_usd,
        )


def _require(data: dict, key: str, cls_name: str, path: str) -> Any:
    if key not in data:
        raise ValueError(f"{cls_name}.from_dict: missing required field '{path}'")
    return data[key]


def _require_mapping(data: dict, key: str, cls_name: str) -> dict:
    value = _require(data, key, cls_name, key)
    if not isinstance(value, dict):
        raise ValueError(
            f"{cls_name}.from_dict: field '{key}' must be a mapping"
        )
    return value
