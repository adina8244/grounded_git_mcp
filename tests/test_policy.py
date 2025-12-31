from __future__ import annotations

import pytest

from grounded_git_mcp.core.errors import GitPolicyError


@pytest.mark.parametrize(
    "args",
    [
        ["push"],
        ["reset", "--hard"],
        ["clean", "-fd"],
        ["checkout", "-f", "main"],
        ["rebase", "--onto", "x", "y"],
    ],
)
def test_policy_blocks_dangerous_commands(tmp_git_repo, args):
    """
    SafeGitRunner should block dangerous subcommands at policy level.
    In your implementation SafeGitRunner(root=...) is required.
    """
    from grounded_git_mcp.core.git_runner import SafeGitRunner

    runner = SafeGitRunner(root=str(tmp_git_repo))

    with pytest.raises(GitPolicyError):
        runner.run(args)


@pytest.mark.parametrize(
    "args",
    [
        ["status", "--porcelain=v1"],
        ["rev-parse", "HEAD"],
        ["log", "-1", "--pretty=format:%h %s"],
        ["ls-tree", "-r", "-t", "--name-only", "HEAD"],
        ["show", "HEAD:README.md"],
    ],
)
def test_policy_allows_safe_read_commands(tmp_git_repo, args):
    """
    Safe read commands should run successfully and return a GitRunResult-like object.
    We assert stable fields rather than exact text.
    """
    from grounded_git_mcp.core.git_runner import SafeGitRunner

    runner = SafeGitRunner(root=str(tmp_git_repo))
    res = runner.run(args)

    assert hasattr(res, "exit_code")
    assert hasattr(res, "stdout")
    assert hasattr(res, "stderr")
    assert hasattr(res, "duration_ms")
    assert hasattr(res, "output_truncated")

    assert isinstance(res.exit_code, int)
    assert res.exit_code == 0


def test_classification_marks_write_commands_as_write():
    """
    classify_git_args returns a dict in your codebase.
    """
    from grounded_git_mcp.core.classification import classify_git_args

    c = classify_git_args(["add", "-A"])

    assert isinstance(c, dict)
    assert c["kind"] in ("write", "read", "network", "destructive")
    assert c["kind"] == "write"
    assert c["risk"] in ("low", "medium", "high", "critical")
    assert isinstance(c.get("reason", ""), str)


def test_classification_marks_read_commands_as_read():
    from grounded_git_mcp.core.classification import classify_git_args

    c = classify_git_args(["status", "--porcelain=v1"])

    assert isinstance(c, dict)
    assert c["kind"] == "read"
    assert c["risk"] in ("low", "medium", "high", "critical")
    assert isinstance(c.get("reason", ""), str)
