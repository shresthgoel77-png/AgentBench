import abc
import os


class WorkspaceSecurityError(Exception):
    """Raised when resolving a path would escape or violate the workspace."""


class Workspace(abc.ABC):
    @abc.abstractmethod
    def create(self, task) -> None:
        """Set up the workspace for the given task."""

    @property
    @abc.abstractmethod
    def root_path(self) -> str:
        """Absolute path to the workspace root."""

    def resolve_path(self, relative_path: str) -> str:
        if os.path.isabs(relative_path):
            raise WorkspaceSecurityError(
                f"absolute paths are not allowed: {relative_path!r}"
            )

        normalized = os.path.normpath(relative_path)
        if normalized == ".." or normalized.startswith(".." + os.sep) or ".." in normalized.split(os.sep):
            raise WorkspaceSecurityError(
                f"path may not contain '..' segments: {relative_path!r}"
            )

        root = os.path.realpath(self.root_path)
        resolved = os.path.realpath(os.path.join(root, normalized))

        if not resolved.startswith(root + os.sep) and resolved != root:
            raise WorkspaceSecurityError(
                f"path escapes the workspace root: {relative_path!r}"
            )

        return resolved

    @abc.abstractmethod
    def cleanup(self) -> None:
        """Remove the workspace and all its contents."""
