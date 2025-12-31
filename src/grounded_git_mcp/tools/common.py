from __future__ import annotations

from pathlib import Path

from ..core.git_runner import GitRunnerConfig, SafeGitRunner
from ..core.security import resolve_root


_DEFAULT_CFG = GitRunnerConfig(timeout_s=3.0, max_output_chars=80_000)


def make_runner(root: str = ".") -> SafeGitRunner:
    return SafeGitRunner(root=resolve_root(root), config=_DEFAULT_CFG)


def clean_lines(s: str) -> list[str]:
    return [ln for ln in s.splitlines() if ln is not None]
