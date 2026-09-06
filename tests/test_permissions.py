import pytest

from agentbench.tasks.schema import TaskSpec
from agentbench.tools.permissions import PermissionChecker


def _task():
    return TaskSpec(
        id="t",
        name="x",
        description="x",
        test_command="pytest",
        readable=["a.txt", "b.txt"],
        writable=["a.txt"],
        max_steps=20,
        max_runtime_seconds=300,
        max_cost_usd=0.5,
    )


def test_allowed_read():
    checker = PermissionChecker(_task())
    checker.check_readable("a.txt")
    assert checker.is_readable("a.txt")


def test_disallowed_read_raises():
    checker = PermissionChecker(_task())
    with pytest.raises(PermissionError) as excinfo:
        checker.check_readable("not_in_list.txt")
    assert "not_in_list.txt" in str(excinfo.value)
    assert not checker.is_readable("not_in_list.txt")


def test_allowed_write():
    checker = PermissionChecker(_task())
    checker.check_writable("a.txt")
    assert checker.is_writable("a.txt")


def test_disallowed_write_raises():
    checker = PermissionChecker(_task())
    with pytest.raises(PermissionError) as excinfo:
        checker.check_writable("b.txt")
    assert "b.txt" in str(excinfo.value)
    assert not checker.is_writable("b.txt")


def test_readable_does_not_imply_writable():
    checker = PermissionChecker(_task())
    assert checker.is_readable("b.txt")
    assert not checker.is_writable("b.txt")
    with pytest.raises(PermissionError):
        checker.check_writable("b.txt")
