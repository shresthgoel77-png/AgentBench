from agentbench.agent.prompts import TOOL_SCHEMAS, build_system_prompt
from agentbench.tasks.schema import TaskSpec


def _task() -> TaskSpec:
    return TaskSpec(
        id="task-007",
        name="Fix the adder",
        description="Make add() handle negative numbers",
        test_command="pytest tests/test_adder.py",
        readable=["src/adder.py", "tasks/README.md"],
        writable=["src/adder.py"],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
    )


def test_system_prompt_contains_task_id():
    prompt = build_system_prompt(_task())
    assert "task-007" in prompt


def test_system_prompt_contains_readable_filenames():
    prompt = build_system_prompt(_task())
    assert "src/adder.py" in prompt
    assert "tasks/README.md" in prompt


def test_system_prompt_contains_writable_filenames():
    prompt = build_system_prompt(_task())
    assert "src/adder.py" in prompt


def test_system_prompt_instructs_to_use_tools_and_finish():
    prompt = build_system_prompt(_task())
    assert "read access" in prompt
    assert "write access" in prompt
    assert "finish" in prompt
    assert "only the provided tools" in prompt


def test_tool_schemas_contains_exactly_five_expected_names():
    names = [tool["name"] for tool in TOOL_SCHEMAS]
    assert len(names) == 5
    assert names == ["read_file", "write_file", "run_tests", "get_git_diff", "finish"]


def test_tool_schemas_have_required_keys():
    for tool in TOOL_SCHEMAS:
        assert {"name", "description", "parameters"} <= set(tool)