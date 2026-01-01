from __future__ import annotations

from pathlib import Path

from ..core.limits import MAX_TREE_ENTRIES
from ..core.security import resolve_root

from ..core.git_runner import SafeGitRunner, require_ok


def repo_tree(root: str = ".", ref: str = "HEAD") -> dict:
    """
    Returns repository tree (paths) at a given ref using `git ls-tree`.
    """
    repo_root = resolve_root(root)
    runner = SafeGitRunner(root)

    res = require_ok(
    runner.run(
        ["ls-tree", "-r", "-t", "--name-only", ref],
        read_only=True,
    ),
    context="repo_tree(ls-tree)",
)


    lines = [ln.strip() for ln in res.stdout.splitlines() if ln.strip()]
    total = len(lines)
    truncated = False
    if total > MAX_TREE_ENTRIES:
        lines = lines[:MAX_TREE_ENTRIES]
        truncated = True

    items = [{"path": p} for p in lines]

    return {
        "root": str(repo_root),
        "ref": ref,
        "total": total,
        "returned": len(items),
        "truncated": truncated,
        "items": items,
        "git": res.__dict__,
    }
