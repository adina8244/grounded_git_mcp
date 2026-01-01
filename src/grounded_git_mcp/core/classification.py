from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


Risk = Literal["low", "medium", "high", "critical"]


@dataclass(frozen=True)
class Classification:
    kind: Literal["read", "write", "network", "destructive"]
    risk: Risk
    reason: str


_DENY = {
    "reset",
    "clean",
    "rebase",
    "commit-tree",
    "update-ref",
    "push",       
    "fetch",      
    "gc",         
}


_WRITE = {"add", "rm", "mv", "commit", "stash", "tag", "branch", "merge", "cherry-pick", "revert"}
_NETWORK = {"push", "fetch", "pull", "clone", "ls-remote", "submodule"}


def classify_git_args(args: list[str]) -> dict:
    """
    args are the git arguments excluding the leading 'git'.
    Example: ["commit", "-m", "msg"]
    """
    if not args:
        return asdict(Classification(kind="read", risk="low", reason="No args."))

    sub = args[0].lower()

    if sub in _DENY:
        return asdict(Classification(kind="destructive", risk="critical", reason=f"Denied subcommand: {sub}"))

    if sub in _NETWORK:
        return asdict(Classification(kind="network", risk="high", reason=f"Network subcommand: {sub}"))

    if sub in _WRITE:
        risk: Risk = "medium" if sub in {"add", "rm", "mv", "tag", "branch", "stash"} else "high"
        return asdict(Classification(kind="write", risk=risk, reason=f"Write subcommand: {sub}"))

    return asdict(Classification(kind="read", risk="low", reason=f"Assumed read-only: {sub}"))
