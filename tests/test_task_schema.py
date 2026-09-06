import pytest

from agentbench.tasks.schema import TaskSpec


def test_valid_dict_produces_correct_taskspec():
    data = {
        "id": "task-001",
        "name": "Fix the adder",
        "description": "Make add() handle negatives",
        "tests": {"command": "pytest tests/test_adder.py"},
        "permissions": {
            "readable": ["src/adder.py", "tasks/README.md"],
            "writable": ["src/adder.py"],
        },
        "limits": {
            "max_steps": 20,
            "max_runtime_seconds": 300,
            "max_cost_usd": 0.5,
        },
    }

    spec = TaskSpec.from_dict(data)

    assert isinstance(spec, TaskSpec)
    assert spec.id == "task-001"
    assert spec.name == "Fix the adder"
    assert spec.description == "Make add() handle negatives"
    assert spec.test_command == "pytest tests/test_adder.py"
    assert spec.readable == ["src/adder.py", "tasks/README.md"]
    assert spec.writable == ["src/adder.py"]
    assert spec.max_steps == 20
    assert spec.max_runtime_seconds == 300
    assert spec.max_cost_usd == 0.5
    assert spec.task_dir == ""


def test_missing_limits_max_steps_raises_with_field_name():
    data = {
        "id": "task-001",
        "name": "Fix the adder",
        "description": "Make add() handle negatives",
        "tests": {"command": "pytest tests/test_adder.py"},
        "permissions": {},
        "limits": {
            "max_runtime_seconds": 300,
            "max_cost_usd": 0.5,
        },
    }

    with pytest.raises(ValueError) as excinfo:
        TaskSpec.from_dict(data)

    assert "max_steps" in str(excinfo.value)
