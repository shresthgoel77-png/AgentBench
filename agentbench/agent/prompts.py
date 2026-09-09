from agentbench.tasks.schema import TaskSpec
TOOL_SCHEMAS: list[dict] = [
    {
        "name": "read_file",
        "description": "Read the contents of a file inside the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the workspace root.",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file inside the workspace.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file, relative to the workspace root.",
                },
                "content": {
                    "type": "string",
                    "description": "Full contents to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_tests",
        "description": "Run the task's test command inside the workspace and return the result.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "get_git_diff",
        "description": "Return the current git diff and list of changed files in the workspace.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "finish",
        "description": "Signal that the task is complete. Call this when done.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Optional summary of what was accomplished.",
                }
            },
            "required": [],
        },
    },
]


def build_system_prompt(task: TaskSpec) -> str:
    readable = ", ".join(task.readable) if task.readable else "(none)"
    writable = ", ".join(task.writable) if task.writable else "(none)"

    return (
        f"You are working on task {task.id!r}: {task.description}\n\n"
        "You have read access to the following files:\n"
        f"{readable}\n\n"
        "You have write access to the following files:\n"
        f"{writable}\n\n"
        "Use only the provided tools to inspect and modify these files. "
        "Do not use tools to access any other files. "
        "Call the \"finish\" tool when the task is done."
    )