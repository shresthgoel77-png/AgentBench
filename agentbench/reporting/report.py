import json
import os
import uuid
from datetime import datetime

from agentbench.tasks.schema import TaskSpec


def _divider(char: str, width: int = 70) -> str:
    return char * width


def _score_line(label: str, score: float) -> str:
    return f"{label:<28} {score:7.1f}"


def format_human_report(task: TaskSpec, agent_label: str, evaluation: dict) -> str:
    header = "=" * 70
    thin = "-" * 40

    lines = []
    lines.append(header)
    lines.append(f"AGENTBENCH RUN REPORT")
    lines.append(f"Task: {task.id} ({task.name})")
    lines.append(f"Agent: {agent_label}")
    lines.append(f"Overall score: {evaluation['overall_score']:.2f}")
    lines.append(f"Task success: {'PASS' if evaluation.get('task_success') else 'FAIL'}")
    lines.append(header)

    lines.append("")
    lines.append("CORRECTNESS")
    lines.append("=" * 40)
    lines.append(f"Task success:  {evaluation.get('task_success')}")
    lines.append(f"Tests passed:  {evaluation.get('tests_passed')} / {evaluation.get('tests_total')}")
    parse_warning = evaluation.get("parse_warning")
    if parse_warning:
        lines.append(f"Parse warning: {parse_warning}")
    lines.append(f"Correctness score: {evaluation.get('score', 0.0):.1f}")

    lines.append("")
    lines.append("EFFICIENCY")
    lines.append("=" * 40)
    lines.append(f"Actions executed:       {evaluation.get('actions')}")
    lines.append(f"Failed actions:         {evaluation.get('failed_actions')}")
    lines.append(f"Unnecessary actions:    {evaluation.get('unnecessary_actions')}")
    lines.append(f"Efficiency score:       {evaluation.get('efficiency_score', 0.0):.1f}")

    lines.append("")
    lines.append("RECOVERY")
    lines.append("=" * 40)
    lines.append(f"Total test failures:    {evaluation.get('total_failures')}")
    lines.append(f"Recovered failures:     {evaluation.get('recovered_failures')}")
    lines.append(f"Recovery rate:          {evaluation.get('recovery_rate', 0.0):.2f}")
    lines.append(f"Recovery score:         {evaluation.get('recovery_score', 0.0):.1f}")

    lines.append("")
    lines.append("SAFETY")
    lines.append("=" * 40)
    lines.append(f"Permission violations:      {evaluation.get('permission_violations')}")
    lines.append(f"Path traversal attempts:    {evaluation.get('path_traversal_attempts')}")
    lines.append(f"Unauthorized files:         {evaluation.get('unauthorized_files')}")
    lines.append(f"Scope compliance:           {evaluation.get('scope_compliance', 0.0):.1f}")
    lines.append(f"Safety score:               {evaluation.get('safety_score', 0.0):.1f}")

    lines.append("")
    lines.append("COST")
    lines.append("=" * 40)
    lines.append(f"Input tokens:   {evaluation.get('input_tokens')}")
    lines.append(f"Output tokens:  {evaluation.get('output_tokens')}")
    lines.append(f"Total tokens:   {evaluation.get('total_tokens')}")
    lines.append(f"Estimated cost: ${evaluation.get('estimated_cost_usd', 0.0):.4f}")
    lines.append(f"Cost score:     {evaluation.get('cost_score', 0.0):.1f}")

    lines.append("")
    lines.append("FINAL SCORE")
    lines.append("=" * 40)
    lines.append(f"Correctness:        {evaluation.get('correctness_score', 0.0):.1f}")
    lines.append(f"Efficiency:         {evaluation.get('efficiency_score', 0.0):.1f}")
    lines.append(f"Recovery:           {evaluation.get('recovery_score', 0.0):.1f}")
    lines.append(f"Safety:             {evaluation.get('safety_score', 0.0):.1f}")
    lines.append(f"Cost:               {evaluation.get('cost_score', 0.0):.1f}")
    lines.append(thin)
    lines.append(f"Overall score:      {evaluation.get('overall_score', 0.0):.2f}")

    return "\n".join(lines)


def build_json_result(
    task: TaskSpec,
    agent_label: str,
    trajectory: list[dict],
    evaluation: dict,
    run_metadata: dict,
) -> dict:
    return {
        "task": {
            "id": task.id,
            "name": task.name,
            "description": task.description,
            "test_command": task.test_command,
            "readable": task.readable,
            "writable": task.writable,
            "max_steps": task.max_steps,
            "max_runtime_seconds": task.max_runtime_seconds,
            "max_cost_usd": task.max_cost_usd,
        },
        "agent": agent_label,
        "model": run_metadata.get("model"),
        "run_id": run_metadata.get("run_id"),
        "started_at": run_metadata.get("started_at"),
        "finished_at": run_metadata.get(
            "finished_at", datetime.utcnow().isoformat()
        ),
        "runtime_seconds": run_metadata.get("runtime_seconds"),
        "trajectory": trajectory,
        "evaluation": evaluation,
    }


def save_result(result: dict, results_dir: str = "results") -> str:
    task_id = result.get("task", {}).get("id", "unknown")
    run_id = result.get("run_id") or uuid.uuid4().hex[:8]
    filename = f"{task_id}_{run_id}.json"
    path = os.path.join(results_dir, filename)

    os.makedirs(results_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return path


def format_markdown_report(result: dict) -> str:
    task = result.get("task") or {}
    evaluation = result.get("evaluation") or {}
    agent_label = result.get("agent") or "unknown"
    model = result.get("model") or "unknown"
    overall = float(evaluation.get("overall_score") or 0.0)
    success = "PASS" if evaluation.get("task_success") else "FAIL"

    lines = []
    lines.append("# AgentBench Run Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Task**: `{task.get('id', 'unknown')}` — {task.get('name', '')}")
    lines.append(f"- **Agent**: {agent_label}")
    lines.append(f"- **Model**: {model}")
    lines.append(f"- **Run ID**: `{result.get('run_id') or 'unknown'}`")
    if result.get("started_at"):
        lines.append(f"- **Started**: {result['started_at']}")
    if result.get("finished_at"):
        lines.append(f"- **Finished**: {result['finished_at']}")
    runtime = result.get("runtime_seconds")
    if runtime is not None:
        lines.append(f"- **Runtime**: {runtime:.2f}s")
    lines.append(f"- **Task success**: {success}")
    lines.append(f"- **Overall score**: **{overall:.2f} / 100**")
    lines.append("")

    description = task.get("description")
    if description:
        lines.append("## Task Description")
        lines.append("")
        lines.append(str(description))
        lines.append("")

    lines.append("## Metric Scores")
    lines.append("")
    lines.append("| Metric | Score |")
    lines.append("|---|---:|")
    metric_rows = [
        ("Correctness", evaluation.get("correctness_score", 0.0)),
        ("Efficiency", evaluation.get("efficiency_score", 0.0)),
        ("Recovery", evaluation.get("recovery_score", 0.0)),
        ("Safety", evaluation.get("safety_score", 0.0)),
        ("Cost", evaluation.get("cost_score", 0.0)),
        ("Runtime", evaluation.get("runtime_score", 0.0)),
        ("Trajectory Quality", evaluation.get("trajectory_quality_score", 0.0)),
    ]
    for label, score in metric_rows:
        lines.append(f"| {label} | {score:.1f} |")
    lines.append(f"| **Overall** | **{overall:.2f}** |")
    lines.append("")

    lines.append("### Correctness")
    lines.append("")
    lines.append(
        f"- Tests passed: {evaluation.get('tests_passed', 0)} / {evaluation.get('tests_total', 0)}"
    )
    lines.append(f"- Task success: {evaluation.get('task_success')}")
    if evaluation.get("parse_warning"):
        lines.append(f"- Parse warning: {evaluation['parse_warning']}")
    lines.append(f"- **Correctness score**: {evaluation.get('correctness_score', 0.0):.1f}")
    lines.append("")

    lines.append("### Efficiency")
    lines.append("")
    lines.append(f"- Actions executed: {evaluation.get('actions', 0)}")
    lines.append(f"- Failed actions: {evaluation.get('failed_actions', 0)}")
    lines.append(f"- Unnecessary actions: {evaluation.get('unnecessary_actions', 0)}")
    lines.append(f"- **Efficiency score**: {evaluation.get('efficiency_score', 0.0):.1f}")
    lines.append("")

    lines.append("### Recovery")
    lines.append("")
    lines.append(f"- Total test failures: {evaluation.get('total_failures', 0)}")
    lines.append(f"- Recovered failures: {evaluation.get('recovered_failures', 0)}")
    lines.append(f"- Recovery rate: {evaluation.get('recovery_rate', 0.0):.2f}")
    lines.append(f"- **Recovery score**: {evaluation.get('recovery_score', 0.0):.1f}")
    lines.append("")

    lines.append("### Safety")
    lines.append("")
    lines.append(f"- Permission violations: {evaluation.get('permission_violations', 0)}")
    lines.append(f"- Path traversal attempts: {evaluation.get('path_traversal_attempts', 0)}")
    lines.append(f"- Unauthorized files: {evaluation.get('unauthorized_files', 0)}")
    lines.append(f"- Scope compliance: {evaluation.get('scope_compliance', 0.0):.1f}")
    lines.append(f"- **Safety score**: {evaluation.get('safety_score', 0.0):.1f}")
    lines.append("")

    lines.append("### Cost")
    lines.append("")
    lines.append(f"- Input tokens: {evaluation.get('input_tokens', 0)}")
    lines.append(f"- Output tokens: {evaluation.get('output_tokens', 0)}")
    lines.append(f"- Total tokens: {evaluation.get('total_tokens', 0)}")
    lines.append(f"- Estimated cost (USD): ${evaluation.get('estimated_cost_usd', 0.0):.4f}")
    lines.append(f"- **Cost score**: {evaluation.get('cost_score', 0.0):.1f}")

    if evaluation.get("error"):
        lines.append("")
        lines.append("### Error")
        lines.append("")
        lines.append(f"- {evaluation['error']}")

    return "\n".join(lines) + "\n"


def save_markdown_report(result: dict, results_dir: str = "results") -> str:
    task_id = result.get("task", {}).get("id", "unknown")
    run_id = result.get("run_id") or uuid.uuid4().hex[:8]
    filename = f"{task_id}_{run_id}.md"
    path = os.path.join(results_dir, filename)

    os.makedirs(results_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(format_markdown_report(result))

    return path
