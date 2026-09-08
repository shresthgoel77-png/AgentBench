import json
import os

import pytest

import run
from agentbench import runner
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


def _write_fake_task(tmp_path, task_id="cli_test"):
    task_dir = tmp_path / "tasks" / task_id
    task_dir.mkdir(parents=True)
    (task_dir / "solution.py").write_text(
        "def answer():\n    return 0\n"
    )
    (task_dir / "test_solution.py").write_text(
        "import solution\n"
        "def test_answer():\n"
        "    assert solution.answer() == 42\n"
    )
    (task_dir / "task.yaml").write_text(
        f"id: {task_id}\n"
        "name: \"CLI Test Task\"\n"
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


class TestPipeline:
    def test_runs_full_pipeline_and_cleans_up(self, tmp_path, monkeypatch, capsys):
        _write_fake_task(tmp_path)
        monkeypatch.chdir(tmp_path)

        script = _script()
        monkeypatch.setattr(
            runner, "get_provider", lambda name, model: ScriptedProvider(script)
        )

        results_dir = tmp_path / "out"
        result = runner.run_single_task(
            "cli_test",
            "anthropic",
            "claude-3-5-sonnet-20241022",
            results_dir=str(results_dir),
        )

        assert result["evaluation"]["task_success"] is True

        output = capsys.readouterr().out
        assert "AGENTBENCH RUN REPORT" in output
        assert "Task success: PASS" in output

        files = sorted(results_dir.glob("*.json"))
        assert len(files) == 1
        data = json.loads(files[0].read_text())
        assert data["task"]["id"] == "cli_test"
        assert data["agent"] == "anthropic/claude-3-5-sonnet-20241022"
        assert data["evaluation"]["task_success"] is True
        assert isinstance(data["trajectory"], list)
        assert len(data["trajectory"]) == 2

        run_id = data["run_id"]
        assert run_id
        assert not os.path.exists(tmp_path / "workspaces" / run_id)

    def test_keep_workspace_leaves_directory(self, tmp_path, monkeypatch):
        _write_fake_task(tmp_path)
        monkeypatch.chdir(tmp_path)

        script = _script()
        monkeypatch.setattr(
            runner, "get_provider", lambda name, model: ScriptedProvider(script)
        )

        results_dir = tmp_path / "out"
        result = runner.run_single_task(
            "cli_test",
            "anthropic",
            "claude-3-5-sonnet-20241022",
            keep_workspace=True,
            results_dir=str(results_dir),
        )

        assert result["evaluation"]["task_success"] is True
        files = sorted(results_dir.glob("*.json"))
        data = json.loads(files[0].read_text())
        run_id = data["run_id"]
        assert os.path.isdir(tmp_path / "workspaces" / run_id)

    def test_verbose_prints_each_step(self, tmp_path, monkeypatch, capsys):
        _write_fake_task(tmp_path)
        monkeypatch.chdir(tmp_path)

        script = _script()
        monkeypatch.setattr(
            runner, "get_provider", lambda name, model: ScriptedProvider(script)
        )

        results_dir = tmp_path / "out"
        result = runner.run_single_task(
            "cli_test",
            "anthropic",
            "claude-3-5-sonnet-20241022",
            verbose=True,
            results_dir=str(results_dir),
        )

        assert result["evaluation"]["task_success"] is True
        output = capsys.readouterr().out
        assert "[step 1] write_file" in output
        assert "[step 2] run_tests" in output

    def test_failed_task_reports_failure(self, tmp_path, monkeypatch):
        task_dir = _write_fake_task(tmp_path)
        task_dir.joinpath("test_solution.py").write_text(
            "import solution\n"
            "def test_answer():\n"
            "    assert False\n"
        )
        monkeypatch.chdir(tmp_path)

        script = _script()
        monkeypatch.setattr(
            runner, "get_provider", lambda name, model: ScriptedProvider(script)
        )

        results_dir = tmp_path / "out"
        result = runner.run_single_task(
            "cli_test",
            "anthropic",
            "claude-3-5-sonnet-20241022",
            results_dir=str(results_dir),
        )

        assert result["evaluation"]["task_success"] is False


class TestCli:
    def test_help_exits_zero(self, capsys):
        with pytest.raises(SystemExit) as excinfo:
            run.main(["--help"])
        assert excinfo.value.code == 0
        out = capsys.readouterr().out
        assert "--model" in out
        assert "--provider" in out
        assert "--keep-workspace" in out
        assert "--verbose" in out

    def test_failed_task_exits_1(self, tmp_path, monkeypatch, capsys):
        _write_fake_task(tmp_path)
        monkeypatch.setattr(
            runner,
            "run_single_task",
            lambda *a, **k: {"evaluation": {"task_success": False}},
        )
        assert run.main(["cli_test"]) == 1

    def test_successful_task_exits_0(self, tmp_path, monkeypatch, capsys):
        _write_fake_task(tmp_path)
        monkeypatch.setattr(
            runner,
            "run_single_task",
            lambda *a, **k: {"evaluation": {"task_success": True}},
        )
        assert run.main(["cli_test"]) == 0