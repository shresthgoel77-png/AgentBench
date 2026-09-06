import pytest

from agentbench.tasks.schema import TaskSpec
from agentbench.tools.testing import run_tests
from agentbench.workspace.local import LocalWorkspace


@pytest.fixture
def task(tmp_path):
    task_dir = tmp_path / "tasks" / "t"
    task_dir.mkdir(parents=True)
    (task_dir / "test_pass.py").write_text(
        "def test_ok():\n    assert True\n"
    )
    (task_dir / "test_fail.py").write_text(
        "def test_fail():\n    assert False\n"
    )
    return task_dir


def _make_workspace(task_dir, tmp_path, monkeypatch, readable=(), writable=()):
    spec = TaskSpec(
        id="t",
        name="x",
        description="x",
        test_command="python3 -m pytest -x",
        readable=list(readable),
        writable=list(writable),
        max_steps=20,
        max_runtime_seconds=60,
        max_cost_usd=1.0,
        task_dir=str(task_dir),
    )
    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)
    return ws, spec


def test_passing_test(tmp_path, task, monkeypatch):
    ws, spec = _make_workspace(
        task, tmp_path, monkeypatch,
        readable=["test_pass.py"],
    )
    try:
        result = run_tests(ws, spec)
    finally:
        ws.cleanup()

    assert result["passed"] is True
    assert result["return_code"] == 0
    assert "test_pass.py" in result["stdout"]
    assert isinstance(result["duration_ms"], int)
    assert result["duration_ms"] >= 0


def test_failing_test(tmp_path, task, monkeypatch):
    ws, spec = _make_workspace(
        task, tmp_path, monkeypatch,
        readable=["test_fail.py"],
    )
    try:
        result = run_tests(ws, spec)
    finally:
        ws.cleanup()

    assert result["passed"] is False
    assert result["return_code"] != 0
    assert "test_fail.py" in result["stdout"]


def test_timeout_never_raises(tmp_path, task, monkeypatch):
    spec = TaskSpec(
        id="t",
        name="x",
        description="x",
        test_command="sleep 10",
        readable=["test_pass.py"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=1,
        max_cost_usd=1.0,
        task_dir=str(task),
    )
    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)
    try:
        result = run_tests(ws, spec)
    finally:
        ws.cleanup()

    assert result["passed"] is False
    assert result["return_code"] is None
    assert "timed out" in result["stderr"]
