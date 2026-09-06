import pytest

from agentbench.workspace.base import Workspace, WorkspaceSecurityError


class StubWorkspace(Workspace):
    def __init__(self, root="/tmp/stub-workspace"):
        self._root = root

    def create(self, task):
        pass

    @property
    def root_path(self):
        return self._root

    def cleanup(self):
        pass


def test_stub_subclass_is_instantiable():
    ws = StubWorkspace()
    assert isinstance(ws, Workspace)


def test_resolve_path_rejects_absolute():
    ws = StubWorkspace("/tmp/ws")
    with pytest.raises(WorkspaceSecurityError):
        ws.resolve_path("/etc/passwd")


def test_resolve_path_rejects_dotdot():
    ws = StubWorkspace("/tmp/ws")
    with pytest.raises(WorkspaceSecurityError):
        ws.resolve_path("../other")


def test_resolve_path_rejects_symlink_escape(tmp_path):
    import os

    outer = tmp_path / "outside"
    outer.mkdir()
    marker = outer / "secret.txt"
    marker.write_text("secret")

    ws_root = tmp_path / "ws"
    ws_root.mkdir()
    (ws_root / "link").symlink_to(outer, target_is_directory=True)

    ws = StubWorkspace(str(ws_root))
    with pytest.raises(WorkspaceSecurityError):
        ws.resolve_path("link/secret.txt")
