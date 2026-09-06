import subprocess

from agentbench.workspace.base import Workspace


def get_git_diff(workspace: Workspace) -> dict:
    diff = subprocess.run(
        ["git", "diff"],
        cwd=workspace.root_path,
        capture_output=True,
        text=True,
    )
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=workspace.root_path,
        capture_output=True,
        text=True,
    )

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
