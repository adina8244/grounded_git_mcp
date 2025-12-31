from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Iterable

import pytest


def _run(cmd: list[str], cwd: Path) -> str:
    out = subprocess.check_output(
        cmd,
        cwd=str(cwd),
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return out.strip()



@pytest.fixture()
def tmp_git_repo(tmp_path: Path) -> Path:
    """
    Creates a small deterministic git repo:
      - 1 initial commit
      - known author identity
      - a couple of files + subdir
    """
    repo = tmp_path / "repo"
    repo.mkdir()

    _run(["git", "init"], repo)
    _run(["git", "config", "user.email", "ci@example.com"], repo)
    _run(["git", "config", "user.name", "CI"], repo)

    (repo / "README.md").write_text("# dummy\n", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "app.py").write_text("print('hi')\n", encoding="utf-8")

    _run(["git", "add", "-A"], repo)
    _run(["git", "commit", "-m", "initial"], repo)

    return repo


@pytest.fixture()
def git_head(tmp_git_repo: Path) -> str:
    return _run(["git", "rev-parse", "HEAD"], tmp_git_repo)


@pytest.fixture()
def make_change(tmp_git_repo: Path):
    """
    Helper: make working tree dirty in a predictable way.
    """
    def _maker(relpath: str = "README.md", text: str = "changed\n") -> Path:
        p = tmp_git_repo / relpath
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p
    return _maker
