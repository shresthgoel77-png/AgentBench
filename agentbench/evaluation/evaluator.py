from agentbench.evaluation.correctness import evaluate_correctness
from agentbench.evaluation.efficiency import evaluate_efficiency
from agentbench.evaluation.recovery import evaluate_recovery
from agentbench.evaluation.safety import evaluate_safety
from agentbench.evaluation.cost import evaluate_cost
from agentbench.evaluation.scoring import (
    compute_overall_score,
    compute_runtime_score,
    compute_trajectory_quality_score,
)
from agentbench.tasks.schema import TaskSpec
from agentbench.tools.gitdiff import get_git_diff
from agentbench.workspace.base import Workspace


def evaluate_run(
    task: TaskSpec,
    workspace: Workspace,
    trajectory: list[dict],
    runtime_seconds: float,
) -> dict:
    correctness = evaluate_correctness(workspace, task)
    efficiency = evaluate_efficiency(trajectory, runtime_seconds)
    recovery = evaluate_recovery(trajectory)
    safety = evaluate_safety(trajectory, task, get_git_diff(workspace))
    cost = evaluate_cost(trajectory, task)
    trajectory_quality_score = compute_trajectory_quality_score(trajectory)
    runtime_score = compute_runtime_score(runtime_seconds, task)

    metric_scores = {
        "correctness": correctness["score"],
        "efficiency": efficiency["score"],
        "safety": safety["score"],
        "recovery": recovery["score"],
        "cost": cost["score"],
        "runtime": runtime_score,
        "trajectory_quality": trajectory_quality_score,
    }

    overall_score = compute_overall_score(metric_scores)
    task_success = correctness["task_success"]

    result = {}
    result.update(correctness)
    result.update(efficiency)
    result.update(recovery)
    result.update(safety)
    result.update(cost)
    result["trajectory_quality_score"] = trajectory_quality_score
    result["runtime_score"] = runtime_score
    result["overall_score"] = overall_score
    result["task_success"] = task_success

    return result
