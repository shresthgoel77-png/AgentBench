import sys
import time
from datetime import datetime

from agentbench.agent.agent import run_agent
from agentbench.agent.llm import get_provider
from agentbench.evaluation.evaluator import evaluate_run
from agentbench.reporting.report import (
    build_json_result,
    format_human_report,
    save_markdown_report,
    save_result,
)
from agentbench.tasks.loader import load_task
from agentbench.tools.permissions import PermissionChecker
from agentbench.trajectory.recorder import TrajectoryRecorder
from agentbench.workspace.local import LocalWorkspace


class _VerboseRecorder(TrajectoryRecorder):
    def record_action(
        self,
        step: int,
        action: str,
        arguments: dict,
        result,
        error: str | None = None,
        duration_ms: int = 0,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        model: str | None = None,
    ) -> None:
        status = "FAILED" if error else "ok"
        print(f"[step {step}] {action}({arguments}) -> {status}")
        super().record_action(
            step=step,
            action=action,
            arguments=arguments,
            result=result,
            error=error,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
        )


def _save_partial_result(
    task,
    agent_label: str,
    workspace,
    recorder,
    started_at: str,
    error: str,
    results_dir: str,
):
    if task is None:
        return None
    trajectory = recorder.as_list() if recorder is not None else []
    run_metadata = {
        "model": None,
        "run_id": workspace.run_id if workspace is not None else None,
        "started_at": started_at,
        "finished_at": datetime.utcnow().isoformat(),
        "runtime_seconds": None,
    }
    partial = build_json_result(
        task,
        agent_label,
        trajectory,
        {"task_success": False, "overall_score": 0.0, "error": error},
        run_metadata,
    )
    return save_result(partial, results_dir=results_dir)


def run_single_task(
    task_id: str,
    provider_name: str,
    model: str,
    keep_workspace: bool = False,
    verbose: bool = False,
    results_dir: str = "results",
) -> dict:
    agent_label = f"{provider_name}/{model}"
    started_at = datetime.utcnow().isoformat()

    task = None
    workspace = None
    recorder = None

    try:
        task = load_task(task_id)

        workspace = LocalWorkspace(keep=keep_workspace)
        workspace.create(task)

        permissions = PermissionChecker(task)
        provider_obj = get_provider(provider_name, model)
        recorder = _VerboseRecorder() if verbose else TrajectoryRecorder()

        start = time.monotonic()
        run_agent(task, workspace, permissions, provider_obj, recorder)
        runtime_seconds = time.monotonic() - start

        evaluation = evaluate_run(task, workspace, recorder.as_list(), runtime_seconds)

        print(format_human_report(task, agent_label, evaluation))

        run_metadata = {
            "model": model,
            "run_id": workspace.run_id,
            "started_at": started_at,
            "finished_at": datetime.utcnow().isoformat(),
            "runtime_seconds": runtime_seconds,
        }
        result = build_json_result(
            task, agent_label, recorder.as_list(), evaluation, run_metadata
        )
        path = save_result(result, results_dir=results_dir)
        md_path = save_markdown_report(result, results_dir=results_dir)
        if verbose:
            print(f"[saved] {path}")
            print(f"[saved markdown] {md_path}")

        return result
    except Exception as exc:
        try:
            _save_partial_result(
                task,
                agent_label,
                workspace,
                recorder,
                started_at,
                str(exc),
                results_dir,
            )
        except Exception:
            print(
                f"[warning] could not save partial result: {exc}",
                file=sys.stderr,
            )
        raise
    finally:
        if workspace is not None:
            workspace.cleanup()
