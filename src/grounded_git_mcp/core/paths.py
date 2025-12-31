from __future__ import annotations

from pathlib import Path


def resolve_root(root: str) -> Path:
    p = Path(root).expanduser().resolve()
    return p


def normalize_relpath(path: str) -> str:
    s = (path or "").strip().replace("\\", "/")
    while s.startswith("./"):
        s = s[2:]
    return s


def ensure_inside_repo(repo_root: Path, relpath: str) -> Path:
    rel = normalize_relpath(relpath)
    abs_path = (repo_root / rel).resolve()
    if repo_root not in abs_path.parents and abs_path != repo_root:
        raise ValueError(f"Path escapes repo root: {relpath}")
    return abs_path
