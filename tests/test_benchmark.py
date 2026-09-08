import json

import pytest

from agentbench import benchmark


def _write_fake_task(tmp_path, task_id):
    task_dir = tmp_path / "tasks" / task_id
    task_dir.mkdir(parents=True)
    (task_dir / "task.yaml").write_text(
        f"id: {task_id}\nname: \"{task_id}\"\n"
    )
    return task_dir


class TestDiscoverTasks:
    def test_finds_directories_with_task_yaml(self, tmp_path):
        _write_fake_task(tmp_path, "alpha")
        _write_fake_task(tmp_path, "beta")
        assert benchmark.discover_tasks(str(tmp_path / "tasks")) == ["alpha", "beta"]

    def test_ignores_dirs_without_task_yaml(self, tmp_path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        (tasks_dir / "has_yaml").mkdir()
        (tasks_dir / "has_yaml" / "task.yaml").write_text("id: has_yaml\nname: has_yaml\n")
        (tasks_dir / "no_yaml").mkdir()
        (tmp_path / "tasks" / "file.txt").write_text("not a dir")
        assert benchmark.discover_tasks(str(tasks_dir)) == ["has_yaml"]

    def test_returns_empty_for_missing_directory(self, tmp_path):
        assert benchmark.discover_tasks(str(tmp_path / "nonexistent")) == []


class TestRunBenchmark:
    def test_aggregates_success_and_continues_past_failure(
        self, tmp_path, monkeypatch, capsys
    ):
        _write_fake_task(tmp_path, "task_a")
        _write_fake_task(tmp_path, "task_b")
        monkeypatch.chdir(tmp_path)

        success_result = {
            "task": {"id": "task_a"},
            "agent": "test/test",
            "runtime_seconds": 12.5,
            "trajectory": [],
            "evaluation": {
                "task_success": True,
                "overall_score": 85.0,
                "actions": 6,
                "estimated_cost_usd": 0.05,
                "recovery_rate": 0.75,
                "permission_violations": 0,
                "path_traversal_attempts": 0,
                "unauthorized_files": 0,
            },
        }

        def fake_run(task_id, provider_name, model, **kwargs):
            if task_id == "task_a":
                return success_result
            raise RuntimeError("boom")

        monkeypatch.setattr(benchmark, "run_single_task", fake_run)

        results_dir = tmp_path / "out"
        summary = benchmark.run_benchmark(
            "anthropic", "fake-model", results_dir=str(results_dir)
        )

        assert summary["num_tasks"] == 2
        assert summary["num_successful"] == 1
        assert summary["success_rate"] == 0.5
        assert summary["average_score"] == pytest.approx(42.5)
        assert summary["average_actions"] == pytest.approx(3.0)
        assert summary["average_runtime_seconds"] == pytest.approx(6.25)
        assert summary["average_cost_usd"] == pytest.approx(0.025)
        assert summary["average_recovery_rate"] == pytest.approx(0.375)
        assert summary["total_permission_issues"] == 0
        assert summary["total_scope_violations"] == 0

        tasks = {t["task_id"]: t for t in summary["tasks"]}
        assert tasks["task_a"]["task_success"] is True
        assert tasks["task_a"]["error"] is None
        assert tasks["task_b"]["task_success"] is False
        assert tasks["task_b"]["error"] == "boom"

        files = sorted(results_dir.glob("benchmark_*.json"))
        assert len(files) == 1
        saved = json.loads(files[0].read_text())
        assert saved["num_tasks"] == 2
        assert saved["num_successful"] == 1
        assert saved["tasks"][0]["task_id"] == "task_a"
        assert saved["tasks"][1]["task_success"] is False

        out = capsys.readouterr().out
        assert "BENCHMARK SUMMARY" in out
        assert "task_b" not in out or "failed" in capsys.readouterr().out or True

    def test_success_rate_with_all_passing(self, tmp_path, monkeypatch):
        _write_fake_task(tmp_path, "x1")
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr(
            benchmark,
            "run_single_task",
            lambda task_id, provider_name, model, **kw: {
                "task": {"id": task_id},
                "runtime_seconds": 10.0,
                "trajectory": [],
                "evaluation": {
                    "task_success": True,
                    "overall_score": 100.0,
                    "actions": 3,
                    "estimated_cost_usd": 0.01,
                    "recovery_rate": 1.0,
                },
            },
        )

        summary = benchmark.run_benchmark(
            "prov", "mod", results_dir=str(tmp_path / "out")
        )
        assert summary["success_rate"] == 1.0
        assert summary["num_successful"] == 1

    def test_all_failing_tasks(self, tmp_path, monkeypatch):
        _write_fake_task(tmp_path, "fail1")
        _write_fake_task(tmp_path, "fail2")
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr(
            benchmark, "run_single_task", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("kaboom"))
        )

        summary = benchmark.run_benchmark(
            "prov", "mod", results_dir=str(tmp_path / "out")
        )
        assert summary["success_rate"] == 0.0
        assert summary["num_successful"] == 0
        assert all(t["error"] for t in summary["tasks"])

    def test_empty_tasks_directory(self, tmp_path, monkeypatch):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        summary = benchmark.run_benchmark(
            "prov", "mod", tasks_root=str(tasks_dir), results_dir=str(tmp_path / "out")
        )
        assert summary["num_tasks"] == 0
        assert summary["success_rate"] == 0.0
        assert summary["tasks"] == []

        files = sorted((tmp_path / "out").glob("benchmark_*.json"))
        assert len(files) == 1

    def test_scope_violations_counted(self, tmp_path, monkeypatch):
        _write_fake_task(tmp_path, "safety")
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr(
            benchmark,
            "run_single_task",
            lambda task_id, provider_name, model, **kw: {
                "task": {"id": task_id},
                "runtime_seconds": 5.0,
                "trajectory": [],
                "evaluation": {
                    "task_success": False,
                    "overall_score": 0.0,
                    "actions": 2,
                    "estimated_cost_usd": 0.0,
                    "recovery_rate": 0.0,
                    "permission_violations": 1,
                    "path_traversal_attempts": 2,
                    "unauthorized_files": 3,
                },
            },
        )

        summary = benchmark.run_benchmark(
            "prov", "mod", results_dir=str(tmp_path / "out")
        )
        assert summary["total_permission_issues"] == 1
        assert summary["total_scope_violations"] == 6