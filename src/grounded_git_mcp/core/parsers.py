from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PorcelainEntry:
    xy: str
    path: str
    orig_path: str | None = None


def parse_status_porcelain(lines: Iterable[str]) -> list[PorcelainEntry]:
    """
    Parses `git status --porcelain=v1 -z` style (but we use newline output for simplicity).
    For v1 lines:
      XY <path>
      XY <path> -> <path2>   (rename)
    """
    out: list[PorcelainEntry] = []
    for raw in lines:
        line = raw.rstrip("\n")
        if not line:
            continue
        xy = line[:2]
        rest = line[3:] if len(line) >= 4 else ""
        if " -> " in rest:
            a, b = rest.split(" -> ", 1)
            out.append(PorcelainEntry(xy=xy, path=b, orig_path=a))
        else:
            out.append(PorcelainEntry(xy=xy, path=rest))
    return out


def diff_summary_from_name_status(lines: Iterable[str]) -> dict:
    """
    Parses `git diff --name-status` lines:
      M\tfile
      A\tfile
      D\tfile
      R100\told\tnew
    Returns a compact summary.
    """
    files: list[dict] = []
    counts: dict[str, int] = {}
    for raw in lines:
        line = raw.strip()
        if not line:
            continue
        parts = line.split("\t")
        code = parts[0]
        counts[code[0]] = counts.get(code[0], 0) + 1
        if code.startswith("R") and len(parts) >= 3:
            files.append({"status": code, "from": parts[1], "to": parts[2]})
        else:
            files.append({"status": code, "path": parts[1] if len(parts) > 1 else ""})
    return {"counts": counts, "files": files, "total": sum(counts.values())}


def detect_conflicts_from_unmerged(lines: Iterable[str]) -> list[str]:
    """
    Parses `git diff --name-only --diff-filter=U` output.
    """
    out: list[str] = []
    for raw in lines:
        p = raw.strip()
        if p:
            out.append(p)
    return out
