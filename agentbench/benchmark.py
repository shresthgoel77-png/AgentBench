import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from agentbench.runner import run_single_task


def discover_tasks(tasks_root: str = "tasks") -> list[str]:
    root = Path(tasks_root)
    if not root.is_dir():
        return []
    return sorted(
        task_dir.name
        for task_dir in root.iterdir()
        if task_dir.is_dir() and (task_dir / "task.yaml").is_file()
    )


def _record_from_result(task_id: str, result: dict) -> dict:
    evaluation = result.get("evaluation") or {}
    scope_violations = (
        int(evaluation.get("permission_violations") or 0)
        + int(evaluation.get("path_traversal_attempts") or 0)
        + int(evaluation.get("unauthorized_files") or 0)
    )
    return {
        "task_id": task_id,
        "task_success": bool(evaluation.get("task_success")),
        "overall_score": float(evaluation.get("overall_score") or 0.0),
        "actions": int(evaluation.get("actions") or 0),
        "runtime_seconds": float(result.get("runtime_seconds") or 0.0),
        "estimated_cost_usd": float(evaluation.get("estimated_cost_usd") or 0.0),
        "recovery_rate": float(evaluation.get("recovery_rate") or 0.0),
        "permission_violations": int(evaluation.get("permission_violations") or 0),
        "scope_violations": scope_violations,
        "error": None,
    }


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def _save_summary(summary: dict, results_dir: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = Path(results_dir) / f"benchmark_{timestamp}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _format_summary(summary: dict) -> str:
    lines = [
        "=" * 46,
        "BENCHMARK SUMMARY",
        f"Provider:         {summary['provider']}",
        f"Model:            {summary['model']}",
        f"Tasks:            {summary['num_tasks']}",
        f"Successful:       {summary['num_successful']}",
        f"Success rate:     {summary['success_rate']:.1%}",
        f"Average score:    {summary['average_score']:.2f}",
        f"Average actions:  {summary['average_actions']:.2f}",
        f"Avg runtime (s):  {summary['average_runtime_seconds']:.2f}",
        f"Avg cost (USD):   {summary['average_cost_usd']:.4f}",
        f"Avg recovery:     {summary['average_recovery_rate']:.2f}",
        f"Permission issues:{summary['total_permission_issues']}",
        f"Scope violations: {summary['total_scope_violations']}",
        "=" * 46,
    ]
    return "\n".join(lines)


def run_benchmark(
    provider_name: str,
    model: str,
    keep_workspace: bool = False,
    verbose: bool = False,
    tasks_root: str = "tasks",
    results_dir: str = "results",
) -> dict:
    task_ids = discover_tasks(tasks_root)

    records = []
    for task_id in task_ids:
        record = {
            "task_id": task_id,
            "task_success": False,
            "overall_score": 0.0,
            "actions": 0,
            "runtime_seconds": 0.0,
            "estimated_cost_usd": 0.0,
            "recovery_rate": 0.0,
            "permission_violations": 0,
            "scope_violations": 0,
            "error": None,
        }
        try:
            result = run_single_task(
                task_id,
                provider_name,
                model,
                keep_workspace=keep_workspace,
                verbose=verbose,
            )
        except Exception as exc:
            record["error"] = str(exc)
            print(f"[benchmark] task '{task_id}' failed: {exc}", file=sys.stderr)
        else:
            record = _record_from_result(task_id, result)
        records.append(record)

    num_tasks = len(records)
    num_successful = sum(1 for r in records if r["task_success"])

    summary = {
        "provider": provider_name,
        "model": model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_tasks": num_tasks,
        "num_successful": num_successful,
        "success_rate": num_successful / num_tasks if num_tasks else 0.0,
        "average_score": _mean(r["overall_score"] for r in records),
        "average_actions": _mean(r["actions"] for r in records),
        "average_runtime_seconds": _mean(r["runtime_seconds"] for r in records),
        "average_cost_usd": _mean(r["estimated_cost_usd"] for r in records),
        "average_recovery_rate": _mean(r["recovery_rate"] for r in records),
        "total_permission_issues": sum(r["permission_violations"] for r in records),
        "total_scope_violations": sum(r["scope_violations"] for r in records),
        "tasks": records,
    }

    _save_summary(summary, results_dir)
    print(_format_summary(summary))
    return summary