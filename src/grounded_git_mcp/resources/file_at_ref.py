from __future__ import annotations

from ..core.git_runner import SafeGitRunner, require_ok
from ..core.limits import MAX_LINES_TEXT
from ..core.security import resolve_root, normalize_relpath


def read_file_at_ref(root: str = ".", ref: str = "HEAD", path: str = "") -> dict:
    """
    Read a file content at a given git ref without checking out.
    """
    runner = SafeGitRunner(root)

    repo_root = resolve_root(root)
    rel = normalize_relpath(path)
    if not rel:
        raise ValueError("path is required")

    spec = f"{ref}:{rel}"
    res = require_ok(
            runner.run(["show", f"{ref}:{rel}"]),
            context="read_file_at_ref(show)",
        )
    lines = res.stdout.splitlines()
    truncated = False
    if len(lines) > MAX_LINES_TEXT:
        lines = lines[:MAX_LINES_TEXT]
        truncated = True

    content = "\n".join(lines)

    return {
        "root": str(repo_root),
        "ref": ref,
        "path": rel,
        "truncated": truncated,
        "line_count": len(res.stdout.splitlines()),
        "content": content,
        "git": res.__dict__,
    }
