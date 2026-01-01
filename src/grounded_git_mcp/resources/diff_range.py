from __future__ import annotations

from ..core.git_runner import SafeGitRunner, require_ok
from ..core.limits import MAX_LINES_TEXT
from ..core.security import resolve_root, normalize_relpath


def diff_range(
    root: str = ".",
    base: str = "HEAD~1",
    head: str = "HEAD",
    *,
    triple_dot: bool = False,
    pathspec: list[str] | None = None,
) -> dict:
    """
    Compute diff between two refs.
    - base..head : changes in head not in base
    - base...head: changes from merge-base(base, head) to head
    """
    runner = SafeGitRunner(root)

    repo_root = (root)
    rng = f"{base}{'...' if triple_dot else '..'}{head}"

    args = ["diff", "--patch", "--no-color", rng]
    if pathspec:
        # pathspec entries must be clean strings
        cleaned = [normalize_relpath(p) for p in pathspec if (p or "").strip()]
        if cleaned:
            args += ["--", *cleaned]

    res = require_ok(
            runner.run(args),
            context="diff_range(diff)",
        )
    lines = res.stdout.splitlines()
    truncated = False
    if len(lines) > MAX_LINES_TEXT:
        lines = lines[:MAX_LINES_TEXT]
        truncated = True

    return {
        "root": str(repo_root),
        "range": rng,
        "base": base,
        "head": head,
        "triple_dot": triple_dot,
        "pathspec": pathspec or [],
        "truncated": truncated,
        "diff": "\n".join(lines),
        "git": res.__dict__,
    }
