import os
from pathlib import Path

import yaml

from agentbench.tasks.schema import TaskSpec


def load_task(task_id: str, tasks_root: str = "tasks") -> TaskSpec:
    task_dir = Path(tasks_root) / task_id
    task_file = task_dir / "task.yaml"

    if not task_file.exists():
        raise FileNotFoundError(f"task.yaml not found: {task_file}")

    with open(task_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    spec = TaskSpec.from_dict(data)
    spec.task_dir = os.path.abspath(task_dir)
    return spec
