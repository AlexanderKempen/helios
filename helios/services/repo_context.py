from __future__ import annotations

import subprocess
from pathlib import Path

MANIFEST_FILES = [
    "package.json", "pyproject.toml", "setup.py", "Cargo.toml",
    "go.mod", "pom.xml", "build.gradle", "Gemfile", "composer.json",
]

MAX_TREE_DEPTH = 3
MAX_TREE_FILES = 200


def gather_repo_context() -> str | None:
    """Collect lightweight repo signals: file tree, README, and package manifest."""
    root = _find_repo_root()
    if not root:
        return None

    sections: list[str] = []

    tree = _file_tree(root)
    if tree:
        sections.append(f"## File tree\n```\n{tree}\n```")

    readme = _read_readme(root)
    if readme:
        sections.append(f"## README (excerpt)\n{readme}")

    manifest = _read_manifest(root)
    if manifest:
        sections.append(f"## Package manifest\n```\n{manifest}\n```")

    return "\n\n".join(sections) if sections else None


def _find_repo_root() -> Path | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            return Path(result.stdout.strip())
    except Exception:
        pass
    return None


def _file_tree(root: Path, depth: int = MAX_TREE_DEPTH) -> str:
    lines: list[str] = []
    _walk(root, root, lines, depth, 0)
    if len(lines) > MAX_TREE_FILES:
        lines = lines[:MAX_TREE_FILES]
        lines.append(f"... ({MAX_TREE_FILES}+ files, truncated)")
    return "\n".join(lines)


def _walk(root: Path, current: Path, lines: list[str], max_depth: int, depth: int) -> None:
    if depth > max_depth or len(lines) > MAX_TREE_FILES:
        return
    skip = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", "target"}
    indent = "  " * depth
    try:
        entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        return
    for entry in entries:
        if entry.name in skip:
            continue
        if entry.is_dir():
            lines.append(f"{indent}{entry.name}/")
            _walk(root, entry, lines, max_depth, depth + 1)
        else:
            lines.append(f"{indent}{entry.name}")


def _read_readme(root: Path) -> str | None:
    for name in ("README.md", "README.rst", "README.txt", "README"):
        path = root / name
        if path.exists():
            text = path.read_text(errors="ignore")[:2000]
            return text.strip()
    return None


def _read_manifest(root: Path) -> str | None:
    for name in MANIFEST_FILES:
        path = root / name
        if path.exists():
            text = path.read_text(errors="ignore")[:1500]
            return text.strip()
    return None
