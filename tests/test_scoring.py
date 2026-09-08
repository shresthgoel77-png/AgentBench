from agentbench.evaluation.scoring import (
    DEFAULT_WEIGHTS,
    compute_overall_score,
    compute_runtime_score,
    compute_trajectory_quality_score,
)
from agentbench.tasks.schema import TaskSpec


def _task(max_runtime: int = 300) -> TaskSpec:
    return TaskSpec(
        id="t1",
        name="test",
        description="test task",
        test_command="echo ok",
        readable=[],
        writable=[],
        max_steps=10,
        max_runtime_seconds=max_runtime,
        max_cost_usd=1.0,
    )


METRIC_SCORES = {
    "correctness": 100.0,
    "efficiency": 80.0,
    "safety": 90.0,
    "recovery": 70.0,
    "cost": 95.0,
    "runtime": 85.0,
    "trajectory_quality": 75.0,
}


class TestDefaultWeights:
    def test_values_match_spec(self) -> None:
        assert DEFAULT_WEIGHTS == {
            "correctness": 0.45,
            "efficiency": 0.15,
            "safety": 0.15,
            "recovery": 0.10,
            "cost": 0.05,
            "runtime": 0.05,
            "trajectory_quality": 0.05,
        }

    def test_weighted_sum(self) -> None:
        result = compute_overall_score(METRIC_SCORES)
        expected = sum(
            METRIC_SCORES[k] * DEFAULT_WEIGHTS[k] for k in DEFAULT_WEIGHTS
        )
        assert result == expected


class TestCustomWeights:
    def test_override(self) -> None:
        weights = {k: 1 / 7 for k in DEFAULT_WEIGHTS}
        result = compute_overall_score(METRIC_SCORES, weights)
        expected = sum(METRIC_SCORES[k] / 7 for k in METRIC_SCORES)
        assert result == expected

    def test_weights_not_summing_to_one(self) -> None:
        bad = {**DEFAULT_WEIGHTS, "correctness": 0.99}
        try:
            compute_overall_score(METRIC_SCORES, bad)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "1.0" in str(e)


class TestValueErrorPaths:
    def test_missing_key(self) -> None:
        incomplete = {k: 100.0 for k in DEFAULT_WEIGHTS if k != "efficiency"}
        try:
            compute_overall_score(incomplete)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "efficiency" in str(e)

    def test_weights_do_not_sum_to_one(self) -> None:
        bad = {**DEFAULT_WEIGHTS, "correctness": 0.99}
        try:
            compute_overall_score(METRIC_SCORES, bad)
            raise AssertionError("Should have raised ValueError")
        except ValueError as e:
            assert "1.0" in str(e)


class TestTrajectoryQuality:
    def test_all_complete(self) -> None:
        traj = [
            {"action": "a", "arguments": {}, "result": "ok"},
            {"action": "b", "arguments": {}, "result": "ok"},
        ]
        assert compute_trajectory_quality_score(traj) == 100.0

    def test_empty_trajectory(self) -> None:
        assert compute_trajectory_quality_score([]) == 100.0

    def test_missing_result(self) -> None:
        traj = [{"action": "a", "arguments": {}}]
        assert compute_trajectory_quality_score(traj) == 90.0

    def test_missing_action(self) -> None:
        traj = [{"arguments": {}, "result": "ok"}]
        assert compute_trajectory_quality_score(traj) == 90.0

    def test_multiple_penalties(self) -> None:
        traj = [{"action": "a"}, {"arguments": {}}, {"result": "ok"}]
        assert compute_trajectory_quality_score(traj) == 70.0

    def test_floors_at_zero(self) -> None:
        traj = [{}] * 11
        assert compute_trajectory_quality_score(traj) == 0.0


class TestRuntimeScore:
    def test_within_limit(self) -> None:
        assert compute_runtime_score(100, _task(max_runtime=300)) == 100.0

    def test_exactly_at_limit(self) -> None:
        assert compute_runtime_score(300, _task(max_runtime=300)) == 100.0

    def test_over_limit_linear(self) -> None:
        task = _task(max_runtime=200)
        assert compute_runtime_score(300, task) == 50.0

    def test_far_over_limit_floors_at_zero(self) -> None:
        assert compute_runtime_score(600, _task(max_runtime=100)) == 0.0
