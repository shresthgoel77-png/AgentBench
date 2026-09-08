from agentbench.evaluation.recovery import evaluate_recovery


def _test_entry(passed: bool) -> dict:
    return {"action": "run_tests", "result": {"passed": passed}, "error": None}


def _other_entry() -> dict:
    return {"action": "read_file", "result": "content", "error": None}


class TestNoFailures:
    def test_empty_trajectory(self) -> None:
        result = evaluate_recovery([])
        assert result == {
            "total_failures": 0,
            "recovered_failures": 0,
            "recovery_rate": 1.0,
            "score": 100.0,
        }

    def test_all_passing(self) -> None:
        trajectory = [_test_entry(True), _other_entry(), _test_entry(True)]
        result = evaluate_recovery(trajectory)
        assert result["total_failures"] == 0
        assert result["recovery_rate"] == 1.0
        assert result["score"] == 100.0


class TestUnrecoveredFailure:
    def test_single_failure_no_later_pass(self) -> None:
        trajectory = [_test_entry(False)]
        result = evaluate_recovery(trajectory)
        assert result == {
            "total_failures": 1,
            "recovered_failures": 0,
            "recovery_rate": 0.0,
            "score": 0.0,
        }

    def test_failure_followed_by_non_test_entry(self) -> None:
        trajectory = [_test_entry(False), _other_entry()]
        result = evaluate_recovery(trajectory)
        assert result["recovery_rate"] == 0.0
        assert result["score"] == 0.0


class TestRecoveredFailure:
    def test_failure_then_pass(self) -> None:
        trajectory = [_test_entry(False), _other_entry(), _test_entry(True)]
        result = evaluate_recovery(trajectory)
        assert result == {
            "total_failures": 1,
            "recovered_failures": 1,
            "recovery_rate": 1.0,
            "score": 100.0,
        }

    def test_failure_then_error_then_pass(self) -> None:
        trajectory = [
            _test_entry(False),
            {"action": "run_tests", "result": None, "error": "timeout"},
            _test_entry(True),
        ]
        result = evaluate_recovery(trajectory)
        assert result["recovered_failures"] == 1
        assert result["recovery_rate"] == 1.0


class TestPartialRecovery:
    def test_two_failures_one_recovered(self) -> None:
        trajectory = [
            _test_entry(False),
            _test_entry(True),  # recovers failure 0
            _test_entry(False),
        ]
        result = evaluate_recovery(trajectory)
        assert result["total_failures"] == 2
        assert result["recovered_failures"] == 1
        assert result["recovery_rate"] == 0.5
        assert result["score"] == 50.0

    def test_three_failures_two_recovered(self) -> None:
        trajectory = [
            _test_entry(False),
            _test_entry(False),
            _test_entry(True),  # recovers failure 0
            _test_entry(True),  # recovers failure 1
            _test_entry(False),
        ]
        result = evaluate_recovery(trajectory)
        assert result["total_failures"] == 3
        assert result["recovered_failures"] == 2
        assert result["recovery_rate"] == 2 / 3
        assert result["score"] == (2 / 3) * 100
