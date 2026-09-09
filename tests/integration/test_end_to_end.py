import json
from pathlib import Path

import pytest

from agentbench import runner
from agentbench.agent.llm import LLMResponse

PROJECT_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_TRAJ_KEYS = [
    "step", "action", "arguments", "result", "error",
    "timestamp", "duration_ms", "input_tokens",
    "output_tokens", "total_tokens", "model",
]
REQUIRED_TRAJ_FIELDS = ["action", "arguments", "result"]


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


FIXED_SOLUTION = "def add(a: int, b: int) -> int:\n    return a + b\n"


def _make_script():
    return [
        {"name": "read_file", "arguments": {"path": "solution.py"}},
        {"name": "write_file", "arguments": {
            "path": "solution.py", "content": FIXED_SOLUTION,
        }},
        {"name": "run_tests", "arguments": {}},
        {"name": "finish", "arguments": {"summary": "Fixed off-by-one error"}},
    ]


class TestEndToEnd:
    def test_full_e2e_with_real_task(self, tmp_path, monkeypatch):
        solution_path = PROJECT_ROOT / "tasks" / "task_001" / "solution.py"
        test_path = PROJECT_ROOT / "tasks" / "task_001" / "test_solution.py"
        orig_solution = solution_path.read_bytes()
        orig_test = test_path.read_bytes()

        monkeypatch.chdir(PROJECT_ROOT)

        script = _make_script()
        monkeypatch.setattr(
            runner, "get_provider",
            lambda name, model: ScriptedProvider(script),
        )

        results_dir = str(tmp_path / "results")
        result = None
        try:
            result = runner.run_single_task(
                "task_001", "fake", "fake-model",
                results_dir=results_dir,
            )
        finally:
            assert solution_path.read_bytes() == orig_solution
            assert test_path.read_bytes() == orig_test

        assert result["evaluation"]["task_success"] is True

        workspaces_dir = PROJECT_ROOT / "workspaces"
        run_id = result["run_id"]
        ws_path = workspaces_dir / run_id
        assert not ws_path.exists(), (
            f"workspace {ws_path} should have been cleaned up"
        )

        result_files = list(Path(results_dir).glob("*.json"))
        assert len(result_files) == 1
        saved = json.loads(result_files[0].read_text())
        assert saved["task"]["id"] == "task_001"
        assert saved["evaluation"]["task_success"] is True

        trajectory = saved["trajectory"]
        assert isinstance(trajectory, list)
        assert len(trajectory) == 3

        for entry in trajectory:
            for key in REQUIRED_TRAJ_KEYS:
                assert key in entry, f"trajectory entry missing key: {key}"
            assert all(
                entry.get(f) is not None for f in REQUIRED_TRAJ_FIELDS
            ), "trajectory entry has None for required field"

        actions = [e["action"] for e in trajectory]
        assert actions == ["read_file", "write_file", "run_tests"]
