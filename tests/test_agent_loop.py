import pytest

from agentbench.agent.agent import run_agent
from agentbench.agent.llm import LLMResponse
from agentbench.tasks.schema import TaskSpec
from agentbench.tools.permissions import PermissionChecker
from agentbench.trajectory.recorder import TrajectoryRecorder
from agentbench.workspace.local import LocalWorkspace


class ScriptedProvider:
    def __init__(self, script):
        self.script = list(script)
        self.generations = 0

    def generate(self, messages, tools, system):
        call = self.script[self.generations]
        self.generations += 1
        if isinstance(call, dict):
            return LLMResponse(
                tool_call=call,
                input_tokens=2,
                output_tokens=3,
                model="fake",
            )
        return call


def _task(tmp_path, max_steps=10, writable=("adder.py",), readable=("adder.py",)):
    task_dir = tmp_path / "tasks" / "t"
    task_dir.mkdir(parents=True)
    (task_dir / "adder.py").write_text("def add():\n    return 1\n")
    return TaskSpec(
        id="t",
        name="Fix the adder",
        description="Make add() handle negatives",
        test_command="python3 -m pytest -q tests/test_adder.py",
        readable=list(readable),
        writable=list(writable),
        max_steps=max_steps,
        max_runtime_seconds=120,
        max_cost_usd=1.0,
        task_dir=str(task_dir),
    )


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    task = _task(tmp_path)
    monkeypatch.chdir(tmp_path)
    ws = LocalWorkspace()
    ws.create(task)
    yield ws, task
    ws.cleanup()


def test_scripted_success_terminates_and_records(workspace):
    ws, task = workspace
    perms = PermissionChecker(task)
    recorder = TrajectoryRecorder()

    provider = ScriptedProvider(
        [
            {"name": "write_file", "arguments": {"path": "adder.py", "content": "def add():\n    return -1\n"}},
            {"name": "run_tests", "arguments": {}},
            {"name": "finish", "arguments": {"summary": "done"}},
        ]
    )

    result = run_agent(task, ws, perms, provider, recorder)

    assert result == {"finished": True, "stop_reason": "finish", "steps_taken": 2}

    actions = recorder.as_list()
    assert len(actions) == 2
    assert [a["action"] for a in actions] == ["write_file", "run_tests"]
    assert actions[0]["error"] is None
    assert actions[1]["error"] is None
    # one trajectory entry per tool call; finish is not a trajectory entry
    assert provider.generations == 3


def test_max_steps_respected_when_never_finish(workspace):
    ws, task = workspace
    perms = PermissionChecker(task)
    recorder = TrajectoryRecorder()

    provider = ScriptedProvider(
        [
            {"name": "run_tests", "arguments": {}},
            {"name": "run_tests", "arguments": {}},
            {"name": "run_tests", "arguments": {}},
            {"name": "run_tests", "arguments": {}},
            {"name": "run_tests", "arguments": {}},
            {"name": "finish", "arguments": {}},
        ]
    )
    task.max_steps = 3

    result = run_agent(task, ws, perms, provider, recorder)

    assert result == {"finished": False, "stop_reason": "max_steps", "steps_taken": 3}


def test_permission_violation_recorded_and_loop_continues(workspace):
    ws, task = workspace
    perms = PermissionChecker(task)
    recorder = TrajectoryRecorder()

    provider = ScriptedProvider(
        [
            {"name": "read_file", "arguments": {"path": "not_allowed.txt"}},
            {"name": "run_tests", "arguments": {}},
            {"name": "finish", "arguments": {}},
        ]
    )

    result = run_agent(task, ws, perms, provider, recorder)

    assert result["finished"] is True
    assert result["stop_reason"] == "finish"
    assert result["steps_taken"] == 2

    actions = recorder.as_list()
    assert len(actions) == 2
    assert actions[0]["action"] == "read_file"
    assert actions[0]["error"] is not None
    assert "read access not allowed" in actions[0]["error"]
    assert actions[1]["error"] is None
