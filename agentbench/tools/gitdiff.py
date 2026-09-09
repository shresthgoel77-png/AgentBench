import subprocess

from agentbench.workspace.base import Workspace


class GitDiffError(Exception):
    """Raised when git commands fail while computing the workspace diff."""


def get_git_diff(workspace: Workspace) -> dict:
    try:
        diff = subprocess.run(
            ["git", "diff"],
            cwd=workspace.root_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=workspace.root_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.SubprocessError, FileNotFoundError) as exc:
        raise GitDiffError(f"git is not available: {exc}") from exc

    if diff.returncode != 0 or status.returncode != 0:
        raise GitDiffError("git commands failed while computing the workspace diff")

    changed_files = []
    for line in status.stdout.splitlines():
        if line.strip():
            parts = line.split(maxsplit=1)
            if len(parts) == 2:
                changed_files.append(parts[1].strip())

    return {
        "diff_text": diff.stdout,
        "changed_files": changed_files,
    }
