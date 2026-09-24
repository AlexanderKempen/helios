import subprocess

BRANCH_PREFIXES = ("feature/", "feat/", "bugfix/", "fix/", "hotfix/")


def strip_branch_prefix(branch: str) -> str:
    for prefix in BRANCH_PREFIXES:
        if branch.startswith(prefix):
            return branch[len(prefix):]
    return branch


def get_current_feature() -> str:
    """Get the current git branch name, stripped of common prefixes."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return "unknown"
        branch = result.stdout.strip()
        if not branch:
            return "unknown"
        return strip_branch_prefix(branch)
    except Exception:
        return "unknown"
