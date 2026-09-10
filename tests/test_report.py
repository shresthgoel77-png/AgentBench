import json
import os

from agentbench.reporting.report import (
    build_json_result,
    format_human_report,
    format_markdown_report,
    save_markdown_report,
    save_result,
)
from agentbench.tasks.schema import TaskSpec


def _task() -> TaskSpec:
    return TaskSpec(
        id="eval_test",
        name="Eval Test",
        description="test task",
        test_command="python3 -m pytest test_eval.py -q",
        readable=["a.txt"],
        writable=["a.txt"],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=5.0,
        task_dir="/tmp/tasks/eval_test",
    )


def _evaluation(task_success: bool) -> dict:
    return {
        "task_success": task_success,
        "tests_passed": 1 if task_success else 0,
        "tests_total": 1,
        "score": 100.0 if task_success else 0.0,
        "actions": 3,
        "failed_actions": 0,
        "unnecessary_actions": 0,
        "runtime_seconds": 10.0,
        "total_failures": 0,
        "recovered_failures": 0,
        "recovery_rate": 1.0,
        "permission_violations": 0,
        "path_traversal_attempts": 0,
        "unauthorized_files": 0,
        "unauthorized_file_list": [],
        "scope_compliance": 100.0,
        "input_tokens": 300,
        "output_tokens": 100,
        "total_tokens": 400,
        "estimated_cost_usd": 0.0012,
        "model": "gpt-4o",
        "trajectory_quality_score": 100.0,
        "runtime_score": 100.0,
        "correctness_score": 100.0 if task_success else 0.0,
        "efficiency_score": 100.0,
        "recovery_score": 100.0,
        "safety_score": 100.0,
        "cost_score": 100.0,
        "overall_score": 100.0 if task_success else 0.0,
    }


def _trajectory() -> list[dict]:
    return [
        {
            "step": 1,
            "action": "read_file",
            "arguments": {"path": "a.txt"},
            "result": "content",
            "error": None,
        }
    ]


SECTION_HEADERS = [
    "CORRECTNESS",
    "EFFICIENCY",
    "RECOVERY",
    "SAFETY",
    "COST",
    "FINAL SCORE",
]


class TestHumanReport:
    def test_contains_all_section_headers(self) -> None:
        report = format_human_report(_task(), "agent-one", _evaluation(True))
        for header in SECTION_HEADERS:
            assert header in report

    def test_uses_divider_styles(self) -> None:
        report = format_human_report(_task(), "agent-one", _evaluation(True))
        assert "=" * 40 in report
        assert "=" * 70 in report
        assert "-" * 40 in report

    def test_renders_task_success_true(self) -> None:
        report = format_human_report(_task(), "agent-one", _evaluation(True))
        assert "Task success: PASS" in report
        assert "AGENTBENCH RUN REPORT" in report

    def test_renders_task_success_false(self) -> None:
        report = format_human_report(_task(), "agent-two", _evaluation(False))
        assert "Task success: FAIL" in report

    def test_agent_label_present(self) -> None:
        report = format_human_report(_task(), "my-agent", _evaluation(True))
        assert "my-agent" in report

    def test_overall_score_present(self) -> None:
        report = format_human_report(_task(), "agent-one", _evaluation(True))
        assert "Overall score:" in report
        assert "100.00" in report


class TestBuildJsonResult:
    def test_has_all_top_level_keys(self) -> None:
        meta = {
            "run_id": "eval_test_run_abc12345",
            "model": "gpt-4o",
            "started_at": "2024-01-01T00:00:00",
            "finished_at": "2024-01-01T00:00:10",
            "runtime_seconds": 10.0,
        }
        result = build_json_result(
            _task(), "agent-one", _trajectory(), _evaluation(True), meta
        )

        assert set(result.keys()) == {
            "task",
            "agent",
            "model",
            "run_id",
            "started_at",
            "finished_at",
            "runtime_seconds",
            "trajectory",
            "evaluation",
        }
        assert result["task"]["id"] == "eval_test"
        assert result["agent"] == "agent-one"
        assert result["run_id"] == "eval_test_run_abc12345"
        assert result["trajectory"] == _trajectory()
        assert result["evaluation"]["overall_score"] == 100.0


class TestSaveResult:
    def test_saves_and_reloads_json(self, tmp_path) -> None:
        meta = {
            "run_id": "eval_test_run_deadbeef",
            "model": "gpt-4o",
            "started_at": "2024-01-01T00:00:00",
            "finished_at": "2024-01-01T00:00:10",
            "runtime_seconds": 10.0,
        }
        result = build_json_result(
            _task(), "agent-one", _trajectory(), _evaluation(True), meta
        )
        path = save_result(result, results_dir=str(tmp_path))

        expected = str(tmp_path / "eval_test_eval_test_run_deadbeef.json")
        assert path == expected
        assert os.path.isfile(path)

        with open(path, encoding="utf-8") as f:
            reloaded = json.load(f)
        assert reloaded == result

    def test_creates_results_dir(self, tmp_path) -> None:
        target = tmp_path / "nested" / "results"
        meta = {"run_id": "eval_test_run_deadbeef"}
        result = build_json_result(
            _task(), "agent-one", _trajectory(), _evaluation(True), meta
        )
        path = save_result(result, results_dir=str(target))
        assert os.path.isfile(path)


class TestMarkdownReport:
    def _result(self, task_success: bool = True, run_id: str = "eval_test_run_deadbeef") -> dict:
        meta = {
            "run_id": run_id,
            "model": "gpt-4o",
            "started_at": "2024-01-01T00:00:00",
            "finished_at": "2024-01-01T00:00:10",
            "runtime_seconds": 10.0,
        }
        return build_json_result(
            _task(), "agent-one", _trajectory(), _evaluation(task_success), meta
        )

    def test_contains_required_findings(self) -> None:
        report = format_markdown_report(self._result())
        assert "# AgentBench Run Report" in report
        assert "eval_test" in report
        assert "agent-one" in report
        assert "Task success**: PASS" in report
        assert "100.00 / 100" in report

    def test_lists_every_metric_score(self) -> None:
        report = format_markdown_report(self._result())
        for metric in [
            "Correctness",
            "Efficiency",
            "Recovery",
            "Safety",
            "Cost",
            "Runtime",
            "Trajectory Quality",
        ]:
            assert f"| {metric} |" in report
        assert "| **Overall** |" in report

    def test_renders_failed_run(self) -> None:
        report = format_markdown_report(self._result(task_success=False))
        assert "Task success**: FAIL" in report
        assert "0.00 / 100" in report

    def test_includes_error_details(self) -> None:
        result = self._result()
        result["evaluation"]["error"] = "provider unavailable"
        report = format_markdown_report(result)
        assert "provider unavailable" in report

    def test_saves_and_reloads_markdown(self, tmp_path) -> None:
        result = self._result()
        path = save_markdown_report(result, results_dir=str(tmp_path))

        expected = str(tmp_path / "eval_test_eval_test_run_deadbeef.md")
        assert path == expected
        assert os.path.isfile(path)

        with open(path, encoding="utf-8") as f:
            reloaded = f.read()
        assert reloaded == format_markdown_report(result)
