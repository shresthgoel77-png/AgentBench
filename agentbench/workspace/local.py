import os
import shutil
import subprocess
import uuid

from agentbench.tasks.schema import TaskSpec
from agentbench.workspace.base import Workspace, WorkspaceSecurityError


class LocalWorkspace(Workspace):
    def __init__(self, keep: bool = False):
        self.keep = keep
        self.run_id = None
        self._root_path = None

    @property
    def root_path(self) -> str:
        return self._root_path

    def create(self, task: TaskSpec) -> None:
        run_id = f"{task.id}_run_{uuid.uuid4().hex[:8]}"
        self.run_id = run_id

        workspaces_dir = os.path.abspath("workspaces")
        os.makedirs(workspaces_dir, exist_ok=True)
        run_dir = os.path.join(workspaces_dir, run_id)
        os.makedirs(run_dir, exist_ok=True)
        self._root_path = run_dir

        if not task.task_dir:
            raise ValueError("task.task_dir is not set; cannot copy task files")

        files = list(dict.fromkeys(task.writable + task.readable))

        for filename in files:
            if "/" in filename or "\\" in filename or ".." in filename:
                raise ValueError(
                    f"task configuration error: invalid file path {filename!r} "
                    "must be a plain filename (no directories or '..' segments)"
                )
            source = os.path.join(task.task_dir, filename)
            if not os.path.isfile(source):
                continue
            shutil.copy2(source, os.path.join(run_dir, filename))

        self._git_init(run_dir)

    def _git_init(self, run_dir: str) -> None:
        subprocess.run(["git", "init", "-q", run_dir], check=True)
        subprocess.run(
            ["git", "-C", run_dir, "add", "-A"], check=True
        )
        env = {
            "GIT_AUTHOR_NAME": "agentbench",
            "GIT_AUTHOR_EMAIL": "agentbench@localhost",
            "GIT_COMMITTER_NAME": "agentbench",
            "GIT_COMMITTER_EMAIL": "agentbench@localhost",
        }
        subprocess.run(
            ["git", "-C", run_dir, "commit", "-q", "-m", "baseline"],
            check=True,
            env=dict(os.environ, **env),
        )

    def cleanup(self) -> None:
        if self.keep:
            return
        if self._root_path and os.path.isdir(self._root_path):
            shutil.rmtree(self._root_path)
            self._root_path = None
