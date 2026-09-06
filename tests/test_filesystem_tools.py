import os

import pytest

from agentbench.tasks.schema import TaskSpec
from agentbench.tools.filesystem import (
    ToolExecutionError,
    read_file,
    write_file,
)
from agentbench.tools.permissions import PermissionChecker
from agentbench.workspace.base import WorkspaceSecurityError
from agentbench.workspace.local import LocalWorkspace


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    task_dir = tmp_path / "tasks" / "t"
    task_dir.mkdir(parents=True)
    (task_dir / "existing.txt").write_text("hello workspace")
    (task_dir / "readable.txt").write_text("readme content")

    spec = TaskSpec(
        id="t",
        name="x",
        description="x",
        test_command="pytest",
        readable=["existing.txt", "readable.txt"],
        writable=["existing.txt"],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)
    yield ws, PermissionChecker(spec)
    ws.cleanup()


def test_successful_read_within_permissions(workspace):
    ws, perms = workspace
    content = read_file(ws, perms, "readable.txt")
    assert content == "readme content"


def test_successful_write_within_permissions(workspace):
    ws, perms = workspace
    write_file(ws, perms, "existing.txt", "updated")
    assert read_file(ws, perms, "existing.txt") == "updated"


def test_out_of_scope_filename_raises_permission_error(workspace):
    ws, perms = workspace
    with pytest.raises(PermissionError):
        read_file(ws, perms, "nonexistent.txt")
    with pytest.raises(PermissionError):
        write_file(ws, perms, "readable.txt", "x")


def test_read_missing_permitted_file_raises_tool_execution_error(tmp_path, monkeypatch):
    spec = TaskSpec(
        id="t4",
        name="x",
        description="x",
        test_command="pytest",
        readable=["missing.txt"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(tmp_path),
    )
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "workspaces" / "t4_run"
    run_dir.mkdir(parents=True)

    ws = _DirectWorkspace(str(run_dir))
    perms = PermissionChecker(spec)
    try:
        with pytest.raises(ToolExecutionError):
            read_file(ws, perms, "missing.txt")
    finally:
        ws.cleanup()


def test_traversal_rejected(tmp_path, monkeypatch):
    outside = tmp_path / "secret.txt"
    outside.write_text("secret")

    spec = TaskSpec(
        id="t5",
        name="x",
        description="x",
        test_command="pytest",
        readable=["link/secret.txt"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(tmp_path),
    )
    monkeypatch.chdir(tmp_path)
    run_dir = tmp_path / "workspaces" / "t5_run"
    run_dir.mkdir(parents=True)
    os.symlink(str(tmp_path), run_dir / "link")

    ws = _DirectWorkspace(str(run_dir))
    perms = PermissionChecker(spec)
    try:
        with pytest.raises(WorkspaceSecurityError):
            read_file(ws, perms, "link/secret.txt")
    finally:
        ws.cleanup()


class _DirectWorkspace(LocalWorkspace):
    def __init__(self, root):
        super().__init__(keep=False)
        self._root_path = root

    def create(self, task):
        self.run_id = f"{task.id}_run"

    @property
    def root_path(self):
        return self._root_path
