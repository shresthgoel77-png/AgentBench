import re
import subprocess

from agentbench.tasks.schema import TaskSpec
from agentbench.tools import testing
from agentbench.workspace.base import Workspace

_PASSED_RE = re.compile(r"(\d+)\s+passed")
_FAILED_RE = re.compile(r"(\d+)\s+failed")


def evaluate_correctness(workspace: Workspace, task: TaskSpec) -> dict:
    result = testing.run_tests(workspace=workspace, task=task)
    passed = bool(result.get("passed"))
    task_success = passed

    parsed = _run_summary_command(workspace, task)

    if parsed is not None:
        tests_passed, tests_total = parsed
        parse_warning = None
    else:
        if task_success:
            tests_passed = 1
            tests_total = 1
        else:
            tests_passed = 0
            tests_total = 0
        parse_warning = "could not parse pytest summary line"

    output = {
        "task_success": task_success,
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "score": 100.0 if task_success else 0.0,
    }
    if parse_warning is not None:
        output["parse_warning"] = parse_warning
    return output


def _run_summary_command(workspace: Workspace, task: TaskSpec):
    timeout = task.max_runtime_seconds
    command = f"{task.test_command} --tb=no -q"
    try:
        proc = subprocess.run(
            command,
            cwd=workspace.root_path,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return None
    except (OSError, subprocess.SubprocessError):
        return None

    combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
    passed_match = _PASSED_RE.search(combined)
    failed_match = _FAILED_RE.search(combined)

    if passed_match is None and failed_match is None:
        return None

    passed_count = int(passed_match.group(1)) if passed_match else 0
    failed_count = int(failed_match.group(1)) if failed_match else 0
    return passed_count, passed_count + failed_count
