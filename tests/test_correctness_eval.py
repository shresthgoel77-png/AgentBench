import pytest

from agentbench.evaluation.correctness import evaluate_correctness
from agentbench.tasks.schema import TaskSpec
from agentbench.workspace.local import LocalWorkspace


def _make_workspace(tmp_path, monkeypatch, test_content):
    task_dir = tmp_path / "tasks" / "t"
    task_dir.mkdir(parents=True)
    (task_dir / "test_foo.py").write_text(test_content)

    spec = TaskSpec(
        id="t",
        name="x",
        description="x",
        test_command="python3 -m pytest test_foo.py",
        readable=["test_foo.py"],
        writable=["test_foo.py"],
        max_steps=20,
        max_runtime_seconds=60,
        max_cost_usd=1.0,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)
    return ws, spec


def test_all_passing_scores_100(tmp_path, monkeypatch):
    content = "def test_ok():\n    assert True\n"
    ws, spec = _make_workspace(tmp_path, monkeypatch, content)
    try:
        result = evaluate_correctness(ws, spec)
    finally:
        ws.cleanup()

    assert result["task_success"] is True
    assert result["tests_passed"] == 1
    assert result["tests_total"] == 1
    assert result["score"] == 100.0
    assert "parse_warning" not in result


def test_all_failing_scores_0(tmp_path, monkeypatch):
    content = "def test_fail():\n    assert False\n"
    ws, spec = _make_workspace(tmp_path, monkeypatch, content)
    try:
        result = evaluate_correctness(ws, spec)
    finally:
        ws.cleanup()

    assert result["task_success"] is False
    assert result["tests_passed"] == 0
    assert result["tests_total"] == 1
    assert result["score"] == 0.0
    assert "parse_warning" not in result
