from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from grounded_git_mcp.core.errors import GitExecutionError, GitPolicyError, InvalidRootError
from grounded_git_mcp.core.git_runner import SafeGitRunner, GitRunnerConfig


def _git(cmd: list[str], cwd: Path) -> str:
    out = subprocess.check_output(
        cmd,
        cwd=str(cwd),
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return out.strip()


def _commit_file(repo: Path, relpath: str, content: str, msg: str) -> None:
    p = repo / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    _git(["git", "add", "-A"], repo)
    _git(["git", "commit", "-m", msg], repo)


def test_git_command_with_nonzero_exit_code(tmp_git_repo: Path):
    runner = SafeGitRunner(tmp_git_repo)

    res = runner.run(["show", "nonexistent_commit_hash_12345"])
    assert res.exit_code != 0
    # stderr may be empty sometimes and error goes to stdout (depends on git),
    # so check combined signal:
    assert ("fatal" in (res.stderr + res.stdout).lower()) or ("error" in (res.stderr + res.stdout).lower())


def test_git_runner_with_nonexistent_repo(tmp_path: Path):
    fake = tmp_path / "nope"
    with pytest.raises(InvalidRootError):
        SafeGitRunner(fake)


def test_git_runner_with_file_instead_of_repo(tmp_path: Path):
    f = tmp_path / "file.txt"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(InvalidRootError):
        SafeGitRunner(f)


def test_git_binary_not_found_raises_gitexecutionerror(tmp_git_repo: Path):
    runner = SafeGitRunner(tmp_git_repo)

    with patch("subprocess.Popen", side_effect=FileNotFoundError("git not found")):
        with pytest.raises(GitExecutionError):
            runner.run(["status"])


def test_git_command_timeout_handling(tmp_git_repo: Path, monkeypatch):
    class FakePopen:
        def __init__(self, *args, **kwargs):
            self.pid = 12345
            self.returncode = None
            self._calls = 0

        def communicate(self, timeout=None):
            self._calls += 1
            if self._calls == 1:
                raise subprocess.TimeoutExpired(cmd="git log --all", timeout=timeout)
            return ("", "")

        def wait(self, timeout=None):
            self.returncode = 0
            return 0

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr(subprocess, "Popen", FakePopen)

    import grounded_git_mcp.core.git_runner as gr
    monkeypatch.setattr(gr, "_kill_process_tree_windows", lambda pid: None)

    config = GitRunnerConfig(timeout_s=0.001)
    runner = SafeGitRunner(tmp_git_repo, config=config)

    res = runner.run(["log", "--all"])
    assert res.timed_out is True
    assert res.exit_code == 124



def test_git_runner_output_truncation_with_large_output(tmp_git_repo: Path):
    _commit_file(tmp_git_repo, "large.txt", "x" * 100_000, "add large")

    config = GitRunnerConfig(max_output_chars=1000)
    runner = SafeGitRunner(tmp_git_repo, config=config)

    res = runner.run(["show", "HEAD:large.txt"])
    assert res.output_truncated is True
    assert (len(res.stdout) + len(res.stderr)) <= 1000


def test_git_runner_stderr_is_captured(tmp_git_repo: Path):
    runner = SafeGitRunner(tmp_git_repo)
    res = runner.run(["log", "nonexistent_ref_xyz"])
    assert res.exit_code != 0
    assert len(res.stderr) > 0 or "fatal" in res.stdout.lower()


def test_git_runner_empty_args_rejected(tmp_git_repo: Path):
    runner = SafeGitRunner(tmp_git_repo)
    with pytest.raises(GitPolicyError):
        runner.run([])


def test_git_runner_read_only_blocks_write_without_flag(tmp_git_repo: Path, make_change):
    runner = SafeGitRunner(tmp_git_repo)
    make_change("x.txt", "data\n")

    with pytest.raises(GitPolicyError):
        runner.run(["add", "x.txt"])  # default read_only should block


def test_git_runner_write_allowed_with_flag(tmp_git_repo: Path, make_change):
    runner = SafeGitRunner(tmp_git_repo)
    make_change("y.txt", "content\n")

    res = runner.run(["add", "y.txt"], read_only=False)
    assert res.exit_code == 0


def test_git_runner_duration_is_measured(tmp_git_repo: Path):
    runner = SafeGitRunner(tmp_git_repo)
    res = runner.run(["status"])
    assert isinstance(res.duration_ms, int)
    assert res.duration_ms >= 0


def test_git_runner_argv_is_recorded(tmp_git_repo: Path):
    runner = SafeGitRunner(tmp_git_repo)
    res = runner.run(["log", "-n", "5"])
    assert res.argv == ["git", "log", "-n", "5"]


def test_git_runner_handles_subprocess_exception(tmp_git_repo: Path):
    runner = SafeGitRunner(tmp_git_repo)

    def mock_communicate(*args, **kwargs):
        raise RuntimeError("Unexpected error")

    with patch("subprocess.Popen") as popen:
        proc = MagicMock()
        proc.communicate = mock_communicate
        proc.pid = 12345
        popen.return_value = proc

        with pytest.raises(GitExecutionError):
            runner.run(["status"])


def test_error_types_inheritance():
    from grounded_git_mcp.core.errors import GroundedGitMCPError, InvalidRootError, GitPolicyError, GitExecutionError
    assert issubclass(InvalidRootError, GroundedGitMCPError)
    assert issubclass(GitPolicyError, GroundedGitMCPError)
    assert issubclass(GitExecutionError, GroundedGitMCPError)
