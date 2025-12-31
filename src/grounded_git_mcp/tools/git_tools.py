from __future__ import annotations

from typing import Any

from .common import clean_lines, make_runner
from ..core.parsers import (
    detect_conflicts_from_unmerged,
    diff_summary_from_name_status,
    parse_status_porcelain,
)


def repo_info(root: str = ".") -> dict[str, Any]:
    """
    High-signal repo metadata: root, is_git, branch, head_sha, upstream (if exists).
    """
    r = make_runner(root)
    is_git = r.run(["rev-parse", "--is-inside-work-tree"]).stdout.strip() == "true"
    if not is_git:
        return {"root": r.root.as_posix(), "is_git": False}

    branch = r.run(["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    head = r.run(["rev-parse", "HEAD"]).stdout.strip()

    # upstream might not exist
    upstream_res = r.run(["rev-parse", "--abbrev-ref", "@{u}"])
    upstream = upstream_res.stdout.strip() if upstream_res.exit_code == 0 else None

    return {
        "root": r.root.as_posix(),
        "is_git": True,
        "branch": branch,
        "head": head,
        "upstream": upstream,
    }


def status_porcelain(root: str = ".", max_entries: int = 200) -> dict[str, Any]:
    """
    Machine-readable status. Perfect for agents.
    """
    r = make_runner(root)
    res = r.run(["status", "--porcelain=v1"])
    entries = parse_status_porcelain(clean_lines(res.stdout))[: max(1, int(max_entries))]
    return {
        "entries": [e.__dict__ for e in entries],
        "count": len(entries),
        "git": res.to_dict(),
    }


def diff_summary(
    root: str = ".",
    staged: bool = False,
    against: str | None = None,
) -> dict[str, Any]:
    """
    Returns a summary of changed file names (name-status).
    - staged=True => --cached
    - against="HEAD" (or any ref) => diff against that ref
    """
    r = make_runner(root)

    args = ["diff", "--name-status"]
    if staged:
        args.append("--cached")
    if against:
        args.append(against)

    res = r.run(args)
    summary = diff_summary_from_name_status(clean_lines(res.stdout))
    return {"summary": summary, "git": res.to_dict()}


def log(
    root: str = ".",
    n: int = 20,
    format: str = "%h %ad %s (%an)",
    date: str = "short",
) -> dict[str, Any]:
    """
    Compact log lines, stable & readable by humans/agents.
    """
    r = make_runner(root)
    n = max(1, min(int(n), 200))
    res = r.run(["log", f"-{n}", f"--pretty=format:{format}", f"--date={date}"])
    return {"lines": clean_lines(res.stdout), "git": res.to_dict()}


def show_commit(
    commit: str,
    root: str = ".",
    patch: bool = True,
    max_chars: int = 12_000,
) -> dict[str, Any]:
    """
    Show one commit. Agents use it to understand changes.
    """
    r = make_runner(root)
    args = ["show", "--stat"]
    if patch:
        args.append("--patch")
    args.append(commit)

    # we already have global output ceiling; this is extra UI-level truncation
    res = r.run(args)
    out = res.stdout
    truncated = False
    if len(out) > max_chars:
        out = out[:max_chars]
        truncated = True

    return {"text": out, "ui_truncated": truncated, "git": res.to_dict()}


def grep(
    pattern: str,
    root: str = ".",
    pathspec: str | None = None,
    ignore_case: bool = False,
    max_hits: int = 200,
) -> dict[str, Any]:
    """
    Git-aware grep (search tracked content fast).
    """
    r = make_runner(root)
    args = ["grep", "-n", "--no-color"]
    if ignore_case:
        args.append("-i")
    args.extend(["-e", pattern])
    if pathspec:
        args.extend(["--", pathspec])

    res = r.run(args)
    lines = clean_lines(res.stdout)
    return {
        "hits": lines[: max(1, int(max_hits))],
        "count": min(len(lines), max(1, int(max_hits))),
        "git": res.to_dict(),
    }


def blame(
    file_path: str,
    root: str = ".",
    start_line: int = 1,
    end_line: int = 200,
) -> dict[str, Any]:
    """
    Blame range for a file. Great for “who changed this line?” debugging.
    """
    r = make_runner(root)
    start_line = max(1, int(start_line))
    end_line = max(start_line, int(end_line))
    rng = f"-L{start_line},{end_line}"

    res = r.run(["blame", "--line-porcelain", rng, "--", file_path])
    # Keep as raw (porcelain) so agents can parse deterministically.
    return {"porcelain": res.stdout, "git": res.to_dict()}


def detect_conflicts(root: str = ".") -> dict[str, Any]:
    """
    Detect merge conflicts (unmerged paths).
    """
    r = make_runner(root)
    res = r.run(["diff", "--name-only", "--diff-filter=U"])
    conflicts = detect_conflicts_from_unmerged(clean_lines(res.stdout))
    return {"conflicts": conflicts, "count": len(conflicts), "git": res.to_dict()}
