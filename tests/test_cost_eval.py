from agentbench.evaluation.cost import evaluate_cost
from agentbench.tasks.schema import TaskSpec


def _task(max_cost: float = 1.0) -> TaskSpec:
    return TaskSpec(
        id="t1",
        name="test",
        description="test",
        test_command="echo ok",
        readable=[],
        writable=[],
        max_steps=10,
        max_runtime_seconds=60,
        max_cost_usd=max_cost,
    )


class TestTokenSummation:
    def test_sums_tokens_across_entries(self) -> None:
        trajectory = [
            {"input_tokens": 100, "output_tokens": 50, "model": "gpt-4o-mini"},
            {"input_tokens": 200, "output_tokens": 30, "model": "gpt-4o-mini"},
            {"input_tokens": None, "output_tokens": None, "model": "gpt-4o-mini"},
        ]
        result = evaluate_cost(trajectory, _task())

        assert result["input_tokens"] == 300
        assert result["output_tokens"] == 80
        assert result["total_tokens"] == 380
        assert result["model"] == "gpt-4o-mini"

    def test_missing_token_fields_count_as_zero(self) -> None:
        trajectory = [{"action": "read_file"}, {"action": "write_file"}]
        result = evaluate_cost(trajectory, _task())

        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        assert result["total_tokens"] == 0
        assert result["model"] == "default"


class TestModelLookup:
    def test_unknown_model_falls_back_to_default(self) -> None:
        trajectory = [
            {"input_tokens": 1000, "output_tokens": 500, "model": "some-unknown-model"},
        ]
        result = evaluate_cost(trajectory, _task())

        assert result["model"] == "some-unknown-model"
        expected = (1000 / 1000) * 0.0005 + (500 / 1000) * 0.0015
        assert result["estimated_cost_usd"] == expected

    def test_first_non_null_model_is_used(self) -> None:
        trajectory = [
            {"model": None, "input_tokens": 100},
            {"model": "gpt-4o", "input_tokens": 100},
            {"model": "gpt-4o-mini", "input_tokens": 100},
        ]
        result = evaluate_cost(trajectory, _task())
        assert result["model"] == "gpt-4o"


class TestMaxCostPenalty:
    def test_score_100_when_under_budget(self) -> None:
        trajectory = [{"input_tokens": 10, "output_tokens": 10, "model": "gpt-4o-mini"}]
        result = evaluate_cost(trajectory, _task(max_cost=1.0))
        assert result["score"] == 100.0

    def test_score_0_when_over_budget(self) -> None:
        trajectory = [{"input_tokens": 1_000_000, "output_tokens": 1_000_000, "model": "gpt-4o"}]
        result = evaluate_cost(trajectory, _task(max_cost=0.01))
        assert result["score"] == 0.0

    def test_score_100_when_exactly_at_budget(self) -> None:
        trajectory = [{"input_tokens": 4000, "output_tokens": 0, "model": "gpt-4o"}]
        result = evaluate_cost(trajectory, _task(max_cost=0.01))
        assert result["score"] == 100.0
