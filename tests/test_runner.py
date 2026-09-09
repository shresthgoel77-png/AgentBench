import json
import os

import pytest

from agentbench import runner
from agentbench.agent.llm import LLMResponse


def _write_fake_task(tmp_path, task_id="runner_task"):
    task_dir = tmp_path / "tasks" / task_id
    task_dir.mkdir(parents=True)
    (task_dir / "solution.py").write_text("x = 1\n")
    (task_dir / "task.yaml").write_text(
        f"id: {task_id}\n"
        "name: \"Runner Task\"\n"
        "description: \"Minimal task\"\n"
        "tests:\n"
        "  command: \"python3 -m pytest -q\"\n"
        "permissions:\n"
        "  readable:\n"
        "    - solution.py\n"
        "  writable:\n"
        "    - solution.py\n"
        "limits:\n"
        "  max_steps: 10\n"
        "  max_runtime_seconds: 120\n"
        "  max_cost_usd: 1.0\n"
    )
    return task_dir


def test_provider_construction_failure_saves_partial_result_with_error(
    tmp_path, monkeypatch
):
    _write_fake_task(tmp_path)
    monkeypatch.chdir(tmp_path)

    def _crash(*a, **k):
        raise RuntimeError("api quota exceeded")

    monkeypatch.setattr(runner, "get_provider", _crash)

    results_dir = tmp_path / "out"
    with pytest.raises(RuntimeError):
        runner.run_single_task(
            "runner_task",
            "anthropic",
            "claude-3-5-sonnet-20241022",
            results_dir=str(results_dir),
        )

    files = sorted(results_dir.glob("runner_task_*.json"))
    assert len(files) == 1
    saved = json.loads(files[0].read_text())
    assert saved["task"]["id"] == "runner_task"
    assert saved["evaluation"]["task_success"] is False
    assert saved["evaluation"]["error"] == "api quota exceeded"

    run_id = saved["run_id"]
    assert run_id
    assert not os.path.exists(tmp_path / "workspaces" / run_id)


def test_task_not_found_saves_no_partial_and_raises(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        runner.run_single_task(
            "missing_task",
            "anthropic",
            "claude-3-5-sonnet-20241022",
            results_dir=str(tmp_path / "out"),
        )
    assert not (tmp_path / "out").exists()


class _ScriptedProvider:
    def __init__(self, script):
        self.script = list(script)
        self.generations = 0

    def generate(self, messages, tools, system):
        call = self.script[self.generations]
        self.generations += 1
        return LLMResponse(tool_call=call, model="fake-model")


def test_provider_error_is_recorded_in_trajectory_and_run_succeeds_harness(
    tmp_path, monkeypatch
):
    _write_fake_task(tmp_path)
    monkeypatch.chdir(tmp_path)

    script = [
        {"name": "write_file", "arguments": {"path": "solution.py", "content": "x = 2\n"}},
        {"name": "finish", "arguments": {}},
    ]
    monkeypatch.setattr(
        runner, "get_provider", lambda name, model: _ScriptedProvider(script)
    )

    result = runner.run_single_task(
        "runner_task",
        "anthropic",
        "claude-3-5-sonnet-20241022",
        results_dir=str(tmp_path / "out"),
    )

    assert result["trajectory"][0]["action"] == "write_file"
    assert result["trajectory"][0]["error"] is None