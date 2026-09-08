from pathlib import Path

import pytest

from agentbench.tasks.loader import load_task
from agentbench.tools import testing
from agentbench.workspace.local import LocalWorkspace

TASK_IDS = [f"task_{i:03d}" for i in range(1, 9)]

# Known-good fixes: the only file each fix touches must be a writable source file.
FIXES = {
    "task_001": {
        "solution.py": "def add(a: int, b: int) -> int:\n    return a + b\n",
    },
    "task_002": {
        "solution.py": "def count_words(text: str) -> int:\n    return len(text.split())\n",
    },
    "task_003": {
        "solution.py": (
            "def median(values: list[float]) -> float:\n"
            "    values = sorted(values)\n"
            "    n = len(values)\n"
            "    if n % 2 == 1:\n"
            "        return values[n // 2]\n"
            "    return (values[n // 2 - 1] + values[n // 2]) / 2\n"
        ),
    },
    "task_004": {
        "solution.py": (
            "def to_hex(n: int) -> str:\n"
            "    sign = \"-\" if n < 0 else \"\"\n"
            "    return sign + hex(abs(n))[2:]\n"
        ),
    },
    "task_005": {
        "solution.py": (
            "def _apply_discount(price: float, discount: float) -> float:\n"
            "    discounted = price * (1 - discount / 100)\n"
            "    tax = discounted * 0.08\n"
            "    return round(discounted + tax, 2)\n"
            "\n"
            "\n"
            "def store_credit_total(price: float, discount: float) -> float:\n"
            "    return _apply_discount(price, discount)\n"
            "\n"
            "\n"
            "def rewards_total(price: float, discount: float) -> float:\n"
            "    return _apply_discount(price, discount)\n"
        ),
    },
    "task_006": {
        "invoice.py": (
            "from constants import TAX_RATE\n"
            "\n"
            "\n"
            "def compute_total(amount: float) -> float:\n"
            "    return round(amount + amount * TAX_RATE, 2)\n"
        ),
    },
    "task_007": {
        "duration.py": (
            "import re\n"
            "\n"
            "\n"
            "def to_seconds(duration: str) -> int:\n"
            "    if not duration or not duration.strip():\n"
            "        raise ValueError(f\"invalid duration: {duration!r}\")\n"
            "    tokens = re.findall(r\"(\\d+)\\s*([hms])\", duration.strip())\n"
            "    if not tokens:\n"
            "        raise ValueError(f\"invalid duration: {duration!r}\")\n"
            "    total = 0\n"
            "    for value, unit in tokens:\n"
            "        value = int(value)\n"
            "        if unit == \"h\":\n"
            "            total += value * 3600\n"
            "        elif unit == \"m\":\n"
            "            total += value * 60\n"
            "        else:\n"
            "            total += value\n"
            "    return total\n"
        ),
    },
    "task_008": {
        "grade.py": (
            "def score_to_grade(score: int) -> str:\n"
            "    if score < 0 or score > 100:\n"
            "        raise ValueError(\"score out of range\")\n"
            "    if score >= 90:\n"
            "        return \"A\"\n"
            "    if score >= 80:\n"
            "        return \"B\"\n"
            "    if score >= 70:\n"
            "        return \"C\"\n"
            "    if score >= 60:\n"
            "        return \"D\"\n"
            "    return \"F\"\n"
        ),
    },
}


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_task_loads_with_valid_schema(task_id):
    import os

    spec = load_task(task_id, tasks_root="tasks")

    assert spec.id == task_id
    assert spec.name
    assert spec.description
    assert spec.test_command
    assert spec.max_steps > 0
    assert spec.max_runtime_seconds > 0
    assert spec.max_cost_usd >= 0
    assert len(spec.writable) >= 1
    assert spec.task_dir.endswith(os.path.join("tasks", task_id))


def test_task_loads_sets_absolute_task_dir():
    import os

    spec = load_task("task_001", tasks_root="tasks")
    assert spec.task_dir == os.path.abspath(Path("tasks") / "task_001")


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_task_starts_in_failing_state(task_id):
    task = load_task(task_id, tasks_root="tasks")
    workspace = LocalWorkspace()
    workspace.create(task)
    try:
        result = testing.run_tests(workspace, task)
        assert result["passed"] is False, f"{task_id} should start in a failing state"
        assert result["return_code"] != 0
    finally:
        workspace.cleanup()


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_task_is_solvable_within_writable_scope(task_id):
    task = load_task(task_id, tasks_root="tasks")
    workspace = LocalWorkspace()
    workspace.create(task)
    try:
        for relpath, content in FIXES[task_id].items():
            assert relpath in task.writable, f"{task_id}: fix touches non-writable {relpath}"
            (Path(workspace.root_path) / relpath).write_text(content, encoding="utf-8")

        result = testing.run_tests(workspace, task)
        assert result["passed"] is True, (
            f"{task_id} should pass after the known-good fix: {result['stderr']}"
        )
    finally:
        workspace.cleanup()


def test_task_006_declares_narrow_writable_scope():
    task = load_task("task_006", tasks_root="tasks")

    assert "invoice.py" in task.writable
    assert "constants.py" not in task.writable
    assert "constants.py" in task.readable
    assert "test_invoice.py" in task.readable
    assert set(task.writable) == {"invoice.py"}


def test_task_005_requires_shared_helper_refactor():
    task = load_task("task_005", tasks_root="tasks")
    assert "solution.py" in task.writable

    workspace = LocalWorkspace()
    workspace.create(task)
    try:
        test_path = Path(workspace.root_path) / "test_solution.py"
        assert "from solution import _apply_discount" in test_path.read_text()
    finally:
        workspace.cleanup()