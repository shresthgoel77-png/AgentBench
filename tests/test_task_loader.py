import os

import pytest

from agentbench.tasks.loader import load_task


def _task_dict():
    return {
        "id": "task_test",
        "name": "Fix the adder",
        "description": "Make add() handle negatives",
        "tests": {"command": "pytest tests/test_adder.py"},
        "permissions": {
            "readable": ["src/adder.py"],
            "writable": ["src/adder.py"],
        },
        "limits": {
            "max_steps": 20,
            "max_runtime_seconds": 300,
            "max_cost_usd": 0.5,
        },
    }


def test_load_task_parses_and_sets_task_dir(tmp_path):
    import yaml

    task_dir = tmp_path / "tasks" / "task_test"
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text(yaml.safe_dump(_task_dict()))

    spec = load_task("task_test", tasks_root=str(tmp_path / "tasks"))

    assert spec.id == "task_test"
    assert spec.name == "Fix the adder"
    assert spec.description == "Make add() handle negatives"
    assert spec.test_command == "pytest tests/test_adder.py"
    assert spec.readable == ["src/adder.py"]
    assert spec.writable == ["src/adder.py"]
    assert spec.max_steps == 20
    assert spec.max_runtime_seconds == 300
    assert spec.max_cost_usd == 0.5
    assert spec.task_dir == os.path.abspath(task_dir)


def test_load_task_missing_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError) as excinfo:
        load_task("missing_task", tasks_root=str(tmp_path / "tasks"))

    assert "task.yaml" in str(excinfo.value)
