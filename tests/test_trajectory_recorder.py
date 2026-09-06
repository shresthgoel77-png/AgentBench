import json

import pytest

from agentbench.trajectory.recorder import TrajectoryRecorder


def test_records_multiple_actions_in_order():
    recorder = TrajectoryRecorder()
    recorder.record_action(
        step=1,
        action="read",
        arguments={"path": "a.txt"},
        result="content",
        error=None,
        duration_ms=10,
        input_tokens=5,
        output_tokens=3,
        model="test-model",
    )
    recorder.record_action(
        step=2,
        action="write",
        arguments={"path": "b.txt", "content": "hello"},
        result=None,
        error=None,
        duration_ms=20,
    )

    actions = recorder.as_list()
    assert len(actions) == 2
    assert [a["step"] for a in actions] == [1, 2]

    first = actions[0]
    assert first["action"] == "read"
    assert first["arguments"] == {"path": "a.txt"}
    assert first["result"] == "content"
    assert first["error"] is None
    assert first["duration_ms"] == 10
    assert first["input_tokens"] == 5
    assert first["output_tokens"] == 3
    assert first["total_tokens"] == 8
    assert first["model"] == "test-model"
    assert "timestamp" in first

    second = actions[1]
    assert second["input_tokens"] is None
    assert second["output_tokens"] is None
    assert second["total_tokens"] is None
    assert second["model"] is None


def test_json_round_trip_via_save_and_reload(tmp_path):
    recorder = TrajectoryRecorder()
    recorder.record_action(
        step=1,
        action="grep",
        arguments={"pattern": "foo"},
        result=["a.py"],
        error=None,
        duration_ms=3,
    )
    recorder.record_action(
        step=2,
        action="bash",
        arguments={"command": "ls"},
        result="",
        error=None,
        duration_ms=4,
        input_tokens=10,
        output_tokens=2,
        model="gpt",
    )

    path = tmp_path / "nested" / "dir" / "trajectory.json"
    recorder.save(str(path))

    assert path.exists()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    assert isinstance(data, list)
    assert len(data) == 2
    assert [a["step"] for a in data] == [1, 2]
    assert data[0]["arguments"] == {"pattern": "foo"}
    assert data[0]["total_tokens"] is None
    assert data[1]["total_tokens"] == 12


def test_failed_action_is_recorded_never_dropped():
    recorder = TrajectoryRecorder()
    recorder.record_action(
        step=1,
        action="edit",
        arguments={"path": "x.py"},
        result=None,
        error="No such file",
        duration_ms=50,
    )
    recorder.record_action(
        step=2,
        action="read",
        arguments={"path": "y.py"},
        result="data",
        error=None,
        duration_ms=1,
    )

    actions = recorder.as_list()
    assert len(actions) == 2
    assert actions[0]["error"] == "No such file"
    assert actions[0]["result"] is None
    assert actions[1]["error"] is None
    assert actions[1]["result"] == "data"
