from agentbench.tasks.schema import TaskSpec


class PermissionChecker:
    def __init__(self, task: TaskSpec):
        self.task = task
        self._readable = set(task.readable)
        self._writable = set(task.writable)

    def check_readable(self, relative_path: str) -> None:
        if not self.is_readable(relative_path):
            raise PermissionError(
                f"read access not allowed: {relative_path!r}"
            )

    def check_writable(self, relative_path: str) -> None:
        if not self.is_writable(relative_path):
            raise PermissionError(
                f"write access not allowed: {relative_path!r}"
            )

    def is_readable(self, path: str) -> bool:
        return path in self._readable

    def is_writable(self, path: str) -> bool:
        return path in self._writable
