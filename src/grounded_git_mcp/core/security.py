from __future__ import annotations

from pathlib import Path

from .errors import InvalidRootError


def resolve_root(root: str | Path) -> Path:
    """Resolve and validate root directory for local-repo operations."""
    p = Path(root).expanduser().resolve()

    if not p.exists():
        raise InvalidRootError(f"Root does not exist: {p}")
    if not p.is_dir():
        raise InvalidRootError(f"Root is not a directory: {p}")

    return p


def normalize_relpath(path: str) -> str:
    """Normalize a user-provided relative path to a safe, consistent form."""
    s = (path or "").strip().replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s

def ensure_within_root(root: Path, target: Path) -> Path:
    """
    Ensure `target` is inside `root` (prevents path traversal).
    Returns resolved target if valid.
    """
    root = root.resolve()
    target = target.expanduser().resolve()

    try:
        target.relative_to(root)
    except ValueError as e:
        raise InvalidRootError(f"Path escapes root. root={root} target={target}") from e

    return target





