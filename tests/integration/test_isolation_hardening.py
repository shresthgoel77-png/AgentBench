import os

import pytest

from agentbench.agent.agent import run_agent
from agentbench.agent.llm import LLMResponse
from agentbench.tasks.schema import TaskSpec
from agentbench.tools.filesystem import read_file, write_file
from agentbench.tools.permissions import PermissionChecker
from agentbench.trajectory.recorder import TrajectoryRecorder
from agentbench.workspace.base import WorkspaceSecurityError
from agentbench.workspace.local import LocalWorkspace


class ScriptedProvider:
    def __init__(self, script):
        self.script = list(script)
        self._idx = 0

    def generate(self, messages, tools, system):
        call = self.script[self._idx]
        self._idx += 1
        return LLMResponse(
            tool_call=call,
            input_tokens=10,
            output_tokens=5,
            model="fake-model",
        )


class _DirectWorkspace(LocalWorkspace):
    """Bypass create() to place files directly into a run directory."""

    def __init__(self, root):
        super().__init__(keep=False)
        self._root_path = root

    def create(self, task):
        self.run_id = f"{task.id}_run"

    @property
    def root_path(self):
        return self._root_path


# ---------------------------------------------------------------------------
# Scenario (a)
# Fake LLM attempts write_file with path-traversal ("../../agentbench/agent/agent.py").
# The attack must be recorded as a trajectory error and the real file unchanged.
# ---------------------------------------------------------------------------
class TestPathTraversalWrite:
    def test_attack_recorded_as_error_and_real_file_unchanged(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.chdir(tmp_path)

        agent_py = tmp_path / "agentbench" / "agent" / "agent.py"
        agent_py.parent.mkdir(parents=True)
        original_content = "# real agent.py\n"
        agent_py.write_text(original_content)

        task_dir = tmp_path / "tasks" / "t"
        task_dir.mkdir(parents=True)
        (task_dir / "solution.py").write_text("x")

        task = TaskSpec(
            id="iso_a",
            name="isolation-a",
            description="path traversal test",
            test_command="true",
            readable=["solution.py"],
            writable=["solution.py"],
            max_steps=5,
            max_runtime_seconds=60,
            max_cost_usd=1.0,
            task_dir=str(task_dir),
        )

        ws = LocalWorkspace()
        ws.create(task)

        recorder = TrajectoryRecorder()
        provider = ScriptedProvider(
            [
                {
                    "name": "write_file",
                    "arguments": {
                        "path": "../../agentbench/agent/agent.py",
                        "content": "INJECTED",
                    },
                },
                {"name": "finish", "arguments": {"summary": "done"}},
            ]
        )

        perms = PermissionChecker(task)
        result = run_agent(task, ws, perms, provider, recorder)

        # The agent loop must have terminated with the attack recorded
        assert result["finished"] is True
        actions = recorder.as_list()
        assert len(actions) == 1
        assert actions[0]["action"] == "write_file"
        assert actions[0]["error"] is not None

        # The real agent.py must be unchanged
        assert agent_py.read_text() == original_content

        ws.cleanup()


# ---------------------------------------------------------------------------
# Scenario (b)
# read_file("/etc/passwd") – absolute path must be rejected before any OS
# call is made.
#
# PRE-EXISTING GAP (Phases 3-4): PermissionChecker.check_readable() runs
# before Workspace.resolve_path(), so "/etc/passwd" is caught by
# PermissionError (not in the readable list) *before* the security-layer
# check can reject it with WorkspaceSecurityError.  The read IS blocked, but
# the rejection comes from the permission layer rather than the path-safety
# layer.  This means an absolute path that *happens* to be in the readable
# list would reach resolve_path — but local.py's create() rejects filenames
# containing '/' so such a task config cannot be produced through normal
# TaskSpec construction.  A defence-in-depth fix would be to call
# resolve_path() before check_readable()/check_writable() in
# filesystem.read_file/write_file, or to add an absolute-path guard inside
# PermissionChecker itself.
# ---------------------------------------------------------------------------
class TestAbsolutePathRejection:
    def test_read_file_rejects_absolute_path(self, tmp_path):
        ws_root = tmp_path / "ws"
        ws_root.mkdir()

        ws = _DirectWorkspace(str(ws_root))
        spec = TaskSpec(
            id="iso_b",
            name="isolation-b",
            description="absolute path test",
            test_command="true",
            readable=["x.txt"],
            writable=[],
            max_steps=5,
            max_runtime_seconds=60,
            max_cost_usd=1.0,
        )
        perms = PermissionChecker(spec)

        # The absolute path IS blocked.  Currently PermissionError fires
        # first (see gap note above); either error confirms the block.
        with pytest.raises((WorkspaceSecurityError, PermissionError)):
            read_file(ws, perms, "/etc/passwd")


# ---------------------------------------------------------------------------
# Scenario (c)
# write_file to a filename not in the task's writable list is rejected by
# PermissionChecker even though the path itself is valid.
# ---------------------------------------------------------------------------
class TestWritePermissionChecker:
    def test_write_to_non_writable_file_rejected(self, tmp_path):
        ws_root = tmp_path / "ws"
        ws_root.mkdir()
        (ws_root / "allowed.txt").write_text("ok")

        ws = _DirectWorkspace(str(ws_root))
        spec = TaskSpec(
            id="iso_c",
            name="isolation-c",
            description="write permission test",
            test_command="true",
            readable=["allowed.txt"],
            writable=["allowed.txt"],
            max_steps=5,
            max_runtime_seconds=60,
            max_cost_usd=1.0,
        )
        perms = PermissionChecker(spec)

        with pytest.raises(PermissionError, match="write access not allowed"):
            write_file(ws, perms, "secrets.txt", "stolen")

        # Confirm nothing was written
        assert not (ws_root / "secrets.txt").exists()


# ---------------------------------------------------------------------------
# Scenario (d)
# A symlink created inside a run directory pointing outside workspaces/ is
# rejected by resolve_path's realpath check.
# ---------------------------------------------------------------------------
class TestSymlinkEscapeRejection:
    def test_symlink_outside_workspaces_rejected(self, tmp_path):
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        (outside_dir / "secret.txt").write_text("stolen")

        ws_root = tmp_path / "workspaces" / "iso_d_run"
        ws_root.mkdir(parents=True)
        os.symlink(str(outside_dir), ws_root / "link", target_is_directory=True)

        ws = _DirectWorkspace(str(ws_root))
        spec = TaskSpec(
            id="iso_d",
            name="isolation-d",
            description="symlink escape test",
            test_command="true",
            readable=["link/secret.txt"],
            writable=[],
            max_steps=5,
            max_runtime_seconds=60,
            max_cost_usd=1.0,
        )
        perms = PermissionChecker(spec)

        with pytest.raises(WorkspaceSecurityError):
            ws.resolve_path("link/secret.txt")
