import os
import subprocess

import pytest

from agentbench.workspace.base import WorkspaceSecurityError
from agentbench.workspace.local import LocalWorkspace


def _build_task(tmp_path, files):
    task_dir = tmp_path / "tasks" / "task_test"
    task_dir.mkdir(parents=True)
    contents = {}
    for name in files:
        data = f"content of {name}".encode()
        (task_dir / name).write_bytes(data)
        contents[name] = data

    data = {
        "id": "task_test",
        "name": "Fix the adder",
        "description": "Make add() handle negatives",
        "tests": {"command": "pytest"},
        "permissions": {
            "readable": files[:],
            "writable": [],
        },
        "limits": {
            "max_steps": 20,
            "max_runtime_seconds": 300,
            "max_cost_usd": 0.5,
        },
    }
    return task_dir, contents


def test_run_directory_created_under_workspaces(tmp_path, monkeypatch):
    import yaml

    task_dir, _ = _build_task(tmp_path, ["a.txt"])
    (task_dir / "task.yaml").write_text(yaml.safe_dump({}))
    from agentbench.tasks.schema import TaskSpec

    spec = TaskSpec(
        id="task_test",
        name="x",
        description="x",
        test_command="pytest",
        readable=["a.txt"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)

    assert ws.run_id is not None
    assert ws.run_id.startswith("task_test_run_")
    run_dir = ws.root_path
    assert os.path.isdir(run_dir)
    assert os.path.dirname(run_dir) == os.path.abspath("workspaces")

    ws.cleanup()
    assert not os.path.exists(run_dir)


def test_only_permitted_files_copied(tmp_path, monkeypatch):
    from agentbench.tasks.schema import TaskSpec

    task_dir, contents = _build_task(tmp_path, ["a.txt", "b.txt", "c.txt"])
    spec = TaskSpec(
        id="task_test",
        name="x",
        description="x",
        test_command="pytest",
        readable=["a.txt"],
        writable=["b.txt"],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)

    copied = set(os.listdir(ws.root_path))
    copied.discard(".git")
    assert copied == {"a.txt", "b.txt"}
    assert (os.path.join(ws.root_path, "a.txt")) and os.path.isfile(
        os.path.join(ws.root_path, "a.txt")
    )
    assert not os.path.exists(os.path.join(ws.root_path, "c.txt"))

    ws.cleanup()


def test_original_task_files_byte_identical_before_after(tmp_path, monkeypatch):
    from agentbench.tasks.schema import TaskSpec

    task_dir, contents = _build_task(tmp_path, ["a.txt", "b.txt"])
    spec = TaskSpec(
        id="task_test",
        name="x",
        description="x",
        test_command="pytest",
        readable=["a.txt", "b.txt"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)

    for name, data in contents.items():
        assert (task_dir / name).read_bytes() == data

    ws.cleanup()
    for name, data in contents.items():
        assert (task_dir / name).read_bytes() == data


def test_baseline_git_commit_exists(tmp_path, monkeypatch):
    from agentbench.tasks.schema import TaskSpec

    task_dir, _ = _build_task(tmp_path, ["a.txt"])
    spec = TaskSpec(
        id="task_test",
        name="x",
        description="x",
        test_command="pytest",
        readable=["a.txt"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)

    out = subprocess.run(
        ["git", "-C", ws.root_path, "log", "--oneline"],
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0
    assert len(out.stdout.strip().splitlines()) == 1
    assert "baseline" in out.stdout

    ws.cleanup()


def test_resolve_path_rejects_dotdot_and_absolute(tmp_path, monkeypatch):
    from agentbench.tasks.schema import TaskSpec

    task_dir, _ = _build_task(tmp_path, ["a.txt"])
    spec = TaskSpec(
        id="task_test",
        name="x",
        description="x",
        test_command="pytest",
        readable=["a.txt"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)

    with pytest.raises(WorkspaceSecurityError):
        ws.resolve_path("../secret")
    with pytest.raises(WorkspaceSecurityError):
        ws.resolve_path("/etc/passwd")

    ws.cleanup()


def test_resolve_path_rejects_symlink_escape(tmp_path, monkeypatch):
    from agentbench.tasks.schema import TaskSpec

    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_text("secret")

    task_dir, _ = _build_task(tmp_path, ["a.txt"])
    spec = TaskSpec(
        id="task_test",
        name="x",
        description="x",
        test_command="pytest",
        readable=["a.txt"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(spec)

    os.symlink(str(outside), os.path.join(ws.root_path, "escape"))
    with pytest.raises(WorkspaceSecurityError):
        ws.resolve_path("escape/secret.txt")

    ws.cleanup()


def test_cleanup_keeps_directory_when_keep_true(tmp_path, monkeypatch):
    from agentbench.tasks.schema import TaskSpec

    task_dir, _ = _build_task(tmp_path, ["a.txt"])
    spec = TaskSpec(
        id="task_test",
        name="x",
        description="x",
        test_command="pytest",
        readable=["a.txt"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(task_dir),
    )

    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace(keep=True)
    ws.create(spec)

    assert os.path.isdir(ws.root_path)
    ws.cleanup()
    assert os.path.isdir(ws.root_path)


def test_git_init_failure_raises_clear_error(tmp_path, monkeypatch):
    from agentbench.tasks.schema import TaskSpec

    task_dir, _ = _build_task(tmp_path, ["a.txt"])
    spec = TaskSpec(
        id="task_test",
        name="x",
        description="x",
        test_command="pytest",
        readable=["a.txt"],
        writable=[],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
        task_dir=str(task_dir),
    )

    def _no_git(*a, **k):
        raise FileNotFoundError("git: command not found")

    monkeypatch.setattr("agentbench.workspace.local.subprocess.run", _no_git)
    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()

    with pytest.raises(RuntimeError) as excinfo:
        ws.create(spec)
    assert "git is not available" in str(excinfo.value)
