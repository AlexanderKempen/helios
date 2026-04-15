import subprocess


def get_current_feature() -> str:
    """Get the current git branch name, stripped of common prefixes."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        branch = result.stdout.strip()
        if not branch:
            return "unknown"
        for prefix in ("feature/", "feat/", "bugfix/", "fix/", "hotfix/"):
            if branch.startswith(prefix):
                return branch[len(prefix):]
        return branch
    except Exception:
        return "unknown"
