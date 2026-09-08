import json

import pytest

import run
from agentbench import benchmark, runner
from agentbench.agent.llm import LLMResponse


class ScriptedProvider:
    def __init__(self, script):
        self.script = list(script)
        self.generations = 0

    def generate(self, messages, tools, system):
        call = self.script[self.generations]
        self.generations += 1
        return LLMResponse(
            tool_call=call,
            input_tokens=10,
            output_tokens=5,
            model="fake-model",
        )


def _write_fake_task(tmp_path, task_id="task_001"):
    task_dir = tmp_path / "tasks" / task_id
    task_dir.mkdir(parents=True)
    (task_dir / "solution.py").write_text("def answer():\n    return 0\n")
    (task_dir / "test_solution.py").write_text(
        "import solution\n"
        "def test_answer():\n"
        "    assert solution.answer() == 42\n"
    )
    (task_dir / "task.yaml").write_text(
        f"id: {task_id}\n"
        "name: \"Repeated Runs Task\"\n"
        "description: \"A minimal pipeline task\"\n"
        "tests:\n"
        "  command: \"python3 -m pytest -q\"\n"
        "permissions:\n"
        "  readable:\n"
        "    - solution.py\n"
        "  writable:\n"
        "    - solution.py\n"
        "    - test_solution.py\n"
        "limits:\n"
        "  max_steps: 10\n"
        "  max_runtime_seconds: 120\n"
        "  max_cost_usd: 1.0\n"
    )
    return task_dir


def _script():
    return [
        {
            "name": "write_file",
            "arguments": {
                "path": "solution.py",
                "content": "def answer():\n    return 42\n",
            },
        },
        {"name": "run_tests", "arguments": {}},
        {"name": "finish", "arguments": {"summary": "done"}},
    ]


class TestRepeatedRunsCli:
    def test_runs_flag_produces_n_result_files(self, tmp_path, monkeypatch, capsys):
        _write_fake_task(tmp_path)
        monkeypatch.chdir(tmp_path)

        script = _script()
        monkeypatch.setattr(
            runner, "get_provider", lambda name, model: ScriptedProvider(script)
        )

        exit_code = run.main(["task_001", "--runs", "3"])

        assert exit_code == 0

        files = sorted((tmp_path / "results").glob("task_001_*.json"))
        assert len(files) == 3

        run_ids = [json.loads(f.read_text())["run_id"] for f in files]
        assert len(set(run_ids)) == 3

    def test_run_single_task_called_n_times(self, tmp_path, monkeypatch, capsys):
        _write_fake_task(tmp_path)
        monkeypatch.chdir(tmp_path)

        script = _script()
        monkeypatch.setattr(
            runner, "get_provider", lambda name, model: ScriptedProvider(script)
        )

        calls = []
        original = runner.run_single_task

        def spy(task_id, provider_name, model, **kwargs):
            calls.append((task_id, provider_name, model))
            return original(task_id, provider_name, model, **kwargs)

        monkeypatch.setattr(runner, "run_single_task", spy)

        run.main(["task_001", "--runs", "3"])
        assert len(calls) == 3
        assert all(task_id == "task_001" for task_id, _, _ in calls)

    def test_printed_summary_matches_result_files(
        self, tmp_path, monkeypatch, capsys
    ):
        _write_fake_task(tmp_path)
        monkeypatch.chdir(tmp_path)

        script = _script()
        monkeypatch.setattr(
            runner, "get_provider", lambda name, model: ScriptedProvider(script)
        )

        exit_code = run.main(["task_001", "--runs", "3"])
        assert exit_code == 0

        files = sorted((tmp_path / "results").glob("task_001_*.json"))
        data = [json.loads(f.read_text()) for f in files]
        evaluations = [d["evaluation"] for d in data]
        n = len(data)
        avg_eval = lambda key: sum(e.get(key) or 0 for e in evaluations) / n
        avg_top = lambda key: sum(d.get(key) or 0 for d in data) / n

        output = capsys.readouterr().out
        assert "REPEATED RUNS SUMMARY" in output
        assert f"Runs:              {n}" in output
        assert f"Successful:        {n}" in output
        assert "Success rate:      100.0%" in output
        assert f"Average score:     {avg_eval('overall_score'):.2f}" in output
        assert f"Average actions:   {avg_eval('actions'):.2f}" in output
        assert f"Avg runtime (s):   {avg_top('runtime_seconds'):.2f}" in output
        assert f"Avg recovery:      {avg_eval('recovery_rate'):.2f}" in output


class TestAggregateRepeatedRuns:
    def test_computes_aggregate_from_records(self):
        records = [
            {
                "task_success": True,
                "overall_score": 80.0,
                "actions": 5,
                "runtime_seconds": 10.0,
                "estimated_cost_usd": 0.01,
                "recovery_rate": 0.8,
                "permission_violations": 0,
                "scope_violations": 0,
            },
            {
                "task_success": False,
                "overall_score": 0.0,
                "actions": 2,
                "runtime_seconds": 6.0,
                "estimated_cost_usd": 0.005,
                "recovery_rate": 0.0,
                "permission_violations": 1,
                "scope_violations": 2,
            },
        ]
        summary = benchmark.aggregate_repeated_runs(records)

        assert summary["num_runs"] == 2
        assert summary["num_successful"] == 1
        assert summary["success_rate"] == 0.5
        assert summary["average_score"] == pytest.approx(40.0)
        assert summary["average_actions"] == pytest.approx(3.5)
        assert summary["average_runtime_seconds"] == pytest.approx(8.0)
        assert summary["average_cost_usd"] == pytest.approx(0.0075)
        assert summary["average_recovery_rate"] == pytest.approx(0.4)
        assert summary["total_permission_issues"] == 1
        assert summary["total_scope_violations"] == 2

    def test_empty_records(self):
        summary = benchmark.aggregate_repeated_runs([])
        assert summary["num_runs"] == 0
        assert summary["num_successful"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["average_score"] == 0.0
        assert summary["average_actions"] == 0.0

    def test_help_lists_runs_flag(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            run.main(["--help"])
        assert excinfo.value.code == 0
        assert "--runs" in capsys.readouterr().out