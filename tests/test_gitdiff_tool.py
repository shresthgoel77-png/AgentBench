import pytest

from agentbench.tasks.schema import TaskSpec
from agentbench.tools.filesystem import write_file
from agentbench.tools.gitdiff import get_git_diff
from agentbench.tools.permissions import PermissionChecker
from agentbench.workspace.local import LocalWorkspace


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    task_dir = tmp_path / "tasks" / "t"
    task_dir.mkdir(parents=True)
    (task_dir / "file.txt").write_text("original content")

    spec = TaskSpec(
        id="t",
        name="x",
        description="x",
        test_command="python3 -m pytest",
        readable=["file.txt"],
        writable=["file.txt"],
        max_steps=20,
        max_runtime_seconds=60,
        max_cost_usd=1.0,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)
    yield ws, spec
    ws.cleanup()


def test_no_changes_gives_empty_diff(workspace):
    ws, _ = workspace
    result = get_git_diff(ws)
    assert result["diff_text"] == ""
    assert result["changed_files"] == []


def test_modified_file_appears_in_diff(workspace):
    ws, spec = workspace
    perms = PermissionChecker(spec)
    write_file(ws, perms, "file.txt", "modified content")

    result = get_git_diff(ws)

    assert "modified content" in result["diff_text"]
    assert "-original content" in result["diff_text"]
    assert "file.txt" in result["changed_files"]
