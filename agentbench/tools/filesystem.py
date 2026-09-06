import os

from agentbench.tools.permissions import PermissionChecker
from agentbench.workspace.base import Workspace


class ToolExecutionError(Exception):
    """Raised when a filesystem tool operation fails at the OS level."""


def read_file(workspace: Workspace, permissions: PermissionChecker, path: str) -> str:
    permissions.check_readable(path)
    resolved = workspace.resolve_path(path)
    try:
        with open(resolved, "r", encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, UnicodeDecodeError, OSError) as exc:
        raise ToolExecutionError(str(exc)) from exc


def write_file(
    workspace: Workspace,
    permissions: PermissionChecker,
    path: str,
    content: str,
) -> None:
    permissions.check_writable(path)
    resolved = workspace.resolve_path(path)
    try:
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(content)
    except (FileNotFoundError, UnicodeDecodeError, OSError) as exc:
        raise ToolExecutionError(str(exc)) from exc
