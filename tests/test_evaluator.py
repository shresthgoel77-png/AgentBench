import os

import pytest

from agentbench.evaluation.evaluator import evaluate_run
from agentbench.tasks.schema import TaskSpec
from agentbench.workspace.local import LocalWorkspace


def _build_task(tmp_path, files, *, test_content="def test_ok(): assert True\n"):
    task_dir = tmp_path / "tasks" / "eval_test"
    task_dir.mkdir(parents=True)
    for name in files:
        (task_dir / name).write_text(f"content of {name}")
    (task_dir / "test_eval.py").write_text(test_content)

    return TaskSpec(
        id="eval_test",
        name="Eval Test",
        description="test task",
        test_command="python3 -m pytest test_eval.py -q",
        readable=files[:],
        writable=files[:],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=5.0,
        task_dir=str(task_dir),
    )


def _make_trajectory():
    return [
        {
            "step": 1,
            "action": "read_file",
            "arguments": {"path": "a.txt"},
            "result": "content of a.txt",
            "error": None,
            "timestamp": "2024-01-01T00:00:00",
            "duration_ms": 10,
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150,
            "model": "gpt-4o",
        },
        {
            "step": 2,
            "action": "write_file",
            "arguments": {"path": "a.txt", "content": "updated"},
            "result": None,
            "error": "PermissionError: access denied",
            "timestamp": "2024-01-01T00:00:01",
            "duration_ms": 5,
            "input_tokens": 80,
            "output_tokens": 20,
            "total_tokens": 100,
            "model": "gpt-4o",
        },
        {
            "step": 3,
            "action": "run_tests",
            "arguments": {},
            "result": {"passed": False},
            "error": None,
            "timestamp": "2024-01-01T00:00:02",
            "duration_ms": 500,
            "input_tokens": 50,
            "output_tokens": 10,
            "total_tokens": 60,
            "model": "gpt-4o",
        },
        {
            "step": 4,
            "action": "read_file",
            "arguments": {"path": "b.txt"},
            "result": "content of b.txt",
            "error": None,
            "timestamp": "2024-01-01T00:00:03",
            "duration_ms": 8,
            "input_tokens": 90,
            "output_tokens": 30,
            "total_tokens": 120,
            "model": "gpt-4o",
        },
    ]


EXPECTED_TOP_KEYS = {
    "task_success",
    "tests_passed",
    "tests_total",
    "score",
    "actions",
    "failed_actions",
    "unnecessary_actions",
    "runtime_seconds",
    "total_failures",
    "recovered_failures",
    "recovery_rate",
    "permission_violations",
    "path_traversal_attempts",
    "unauthorized_files",
    "unauthorized_file_list",
    "scope_compliance",
    "input_tokens",
    "output_tokens",
    "total_tokens",
    "estimated_cost_usd",
    "model",
    "trajectory_quality_score",
    "runtime_score",
    "overall_score",
}


def test_evaluate_run_returns_all_keys(tmp_path, monkeypatch):
    spec = _build_task(tmp_path, ["a.txt", "b.txt"])
    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)
    try:
        result = evaluate_run(spec, ws, _make_trajectory(), 10.0)
    finally:
        ws.cleanup()

    assert EXPECTED_TOP_KEYS.issubset(result.keys())
    assert isinstance(result["overall_score"], float)
    assert isinstance(result["task_success"], bool)


def test_overall_score_in_range(tmp_path, monkeypatch):
    spec = _build_task(tmp_path, ["a.txt", "b.txt"])
    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)
    try:
        result = evaluate_run(spec, ws, _make_trajectory(), 10.0)
    finally:
        ws.cleanup()

    assert 0.0 <= result["overall_score"] <= 100.0


def test_evaluate_run_never_raises_with_errors(tmp_path, monkeypatch):
    spec = _build_task(tmp_path, ["a.txt"])
    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)

    trajectory_with_failures = [
        {
            "step": 1,
            "action": "write_file",
            "arguments": {"path": "a.txt", "content": "x"},
            "result": None,
            "error": "WorkspaceSecurityError: denied",
            "timestamp": "2024-01-01T00:00:00",
            "duration_ms": 1,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "model": None,
        },
        {
            "step": 2,
            "action": "run_tests",
            "arguments": {},
            "result": None,
            "error": "subprocess timed out",
            "timestamp": "2024-01-01T00:00:01",
            "duration_ms": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "model": None,
        },
        {
            "step": 3,
            "action": "run_tests",
            "arguments": {},
            "result": {"passed": False},
            "error": None,
            "timestamp": "2024-01-01T00:00:02",
            "duration_ms": 100,
            "input_tokens": 10,
            "output_tokens": 5,
            "total_tokens": 15,
            "model": None,
        },
    ]

    try:
        result = evaluate_run(spec, ws, trajectory_with_failures, 5.0)
    finally:
        ws.cleanup()

    assert "overall_score" in result
    assert 0.0 <= result["overall_score"] <= 100.0
    assert isinstance(result["task_success"], bool)


def test_empty_trajectory(tmp_path, monkeypatch):
    spec = _build_task(tmp_path, ["a.txt"])
    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)
    try:
        result = evaluate_run(spec, ws, [], 0.1)
    finally:
        ws.cleanup()

    assert 0.0 <= result["overall_score"] <= 100.0
    assert result["actions"] == 0
    assert result["trajectory_quality_score"] == 100.0
