import subprocess
import time

from agentbench.tasks.schema import TaskSpec
from agentbench.workspace.base import Workspace


def run_tests(workspace: Workspace, task: TaskSpec) -> dict:
    timeout = task.max_runtime_seconds
    start = time.monotonic()
    try:
        proc = subprocess.run(
            task.test_command,
            cwd=workspace.root_path,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return {
            "passed": proc.returncode == 0,
            "return_code": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "duration_ms": int((time.monotonic() - start) * 1000),
        }
    except subprocess.TimeoutExpired as exc:
        stderr = (exc.stderr or "") or ""
        if not stderr.strip():
            stderr = f"test command timed out after {timeout} seconds"
        return {
            "passed": False,
            "return_code": None,
            "stdout": exc.stdout or "",
            "stderr": stderr,
            "duration_ms": int((time.monotonic() - start) * 1000),
        }
