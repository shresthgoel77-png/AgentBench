from agentbench.evaluation.efficiency import evaluate_efficiency


def _make_entry(action: str, arguments: dict, error: str | None = None) -> dict:
    return {"action": action, "arguments": arguments, "error": error}


class TestZeroFailure:
    def test_perfect_score(self) -> None:
        trajectory = [
            _make_entry("read_file", {"path": "a.txt"}),
            _make_entry("write_file", {"path": "b.txt", "content": "hi"}),
            _make_entry("read_file", {"path": "b.txt"}),
        ]
        result = evaluate_efficiency(trajectory, runtime_seconds=1.5)

        assert result == {
            "actions": 3,
            "failed_actions": 0,
            "unnecessary_actions": 0,
            "runtime_seconds": 1.5,
            "score": 100.0,
        }


class TestFailuresAndRepeats:
    def test_penalises_errors_and_repeated_calls(self) -> None:
        trajectory = [
            _make_entry("read_file", {"path": "a.txt"}),
            _make_entry("read_file", {"path": "a.txt"}, error="file not found"),  # repeat
            _make_entry("write_file", {"path": "b.txt", "content": "x"}),
            _make_entry("run_tests", {"task_id": "t1"}, error="timeout"),  # failure, no repeat
        ]
        result = evaluate_efficiency(trajectory, runtime_seconds=3.0)

        assert result["actions"] == 4
        assert result["failed_actions"] == 2
        assert result["unnecessary_actions"] == 1
        assert result["runtime_seconds"] == 3.0
        assert result["score"] == 100.0 - 5 * 2 - 5 * 1

    def test_score_never_below_zero(self) -> None:
        trajectory = [_make_entry("fail", {}, error="err")] * 25
        result = evaluate_efficiency(trajectory, runtime_seconds=0.0)

        assert result["score"] == 0.0
        assert result["actions"] == 25
        assert result["failed_actions"] == 25
