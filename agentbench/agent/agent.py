import time

from agentbench.agent.llm import LLMProvider
from agentbench.agent.prompts import TOOL_SCHEMAS, build_system_prompt
from agentbench.tasks.schema import TaskSpec
from agentbench.tools import filesystem, gitdiff, testing
from agentbench.tools.filesystem import ToolExecutionError
from agentbench.tools.gitdiff import GitDiffError
from agentbench.tools.permissions import PermissionChecker
from agentbench.trajectory.recorder import TrajectoryRecorder
from agentbench.workspace.base import Workspace, WorkspaceSecurityError

_TOOL_ERRORS = (
    PermissionError,
    ToolExecutionError,
    WorkspaceSecurityError,
    GitDiffError,
)


def run_agent(
    task: TaskSpec,
    workspace: Workspace,
    permissions: PermissionChecker,
    provider: LLMProvider,
    recorder: TrajectoryRecorder,
) -> dict:
    system = build_system_prompt(task)
    messages: list[dict] = []
    start = time.monotonic()
    steps = 0

    while True:
        if steps >= task.max_steps:
            return {"finished": False, "stop_reason": "max_steps", "steps_taken": steps}

        elapsed = time.monotonic() - start
        if elapsed > task.max_runtime_seconds:
            return {
                "finished": False,
                "stop_reason": "timeout",
                "steps_taken": steps,
            }

        try:
            response = provider.generate(messages=messages, tools=TOOL_SCHEMAS, system=system)
        except Exception as exc:
            steps += 1
            recorder.record_action(
                step=steps,
                action="provider_error",
                arguments={},
                result=None,
                error=str(exc),
            )
            return {
                "finished": False,
                "stop_reason": f"provider_error: {exc}",
                "steps_taken": steps,
            }

        if response.tool_call is None:
            content = response.content if response.content is not None else ""
            messages.append({"role": "assistant", "content": content})
            continue

        tool_name = response.tool_call.get("name")
        arguments = response.tool_call.get("arguments") or {}
        if not isinstance(arguments, dict):
            arguments = {}

        if tool_name == "finish":
            return {"finished": True, "stop_reason": "finish", "steps_taken": steps}

        argument_result = _dispatch_tool(tool_name, arguments, workspace, permissions, task)

        steps += 1

        recorder.record_action(
            step=steps,
            action=argument_result["action"],
            arguments=argument_result["arguments"],
            result=argument_result["result"],
            error=argument_result["error"],
            duration_ms=argument_result["duration_ms"],
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            model=response.model,
        )

        messages.append({"role": "assistant", "content": ""})
        messages.append(
            {
                "role": "user",
                "content": argument_result["message"],
            }
        )


def _dispatch_tool(
    tool_name: str,
    arguments: dict,
    workspace: Workspace,
    permissions: PermissionChecker,
    task: TaskSpec,
) -> dict:
    action_name = tool_name
    started = time.monotonic()

    try:
        if tool_name == "read_file":
            result = filesystem.read_file(
                workspace=workspace, permissions=permissions, path=arguments["path"]
            )
            message = result
            error = None
        elif tool_name == "write_file":
            filesystem.write_file(
                workspace=workspace,
                permissions=permissions,
                path=arguments["path"],
                content=arguments["content"],
            )
            result = {"ok": True}
            message = "wrote file"
            error = None
        elif tool_name == "run_tests":
            result = testing.run_tests(workspace=workspace, task=task)
            message = str(result)
            error = None
        elif tool_name == "get_git_diff":
            result = gitdiff.get_git_diff(workspace=workspace)
            message = str(result)
            error = None
        else:
            result = None
            message = f"unknown tool: {tool_name!r}"
            error = f"unknown tool: {tool_name!r}"
    except _TOOL_ERRORS as exc:
        result = None
        message = f"error: {exc}"
        error = str(exc)

    return {
        "action": action_name,
        "arguments": arguments,
        "result": result,
        "error": error,
        "message": message,
        "duration_ms": int((time.monotonic() - started) * 1000),
    }
