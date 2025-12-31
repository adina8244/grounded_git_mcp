from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from grounded_git_mcp.core.errors import GitPolicyError


def _run(cmd: list[str], cwd: Path) -> str:
    """
    Run git commands in a deterministic Windows-friendly way.
    (UTF-8 decode + replace to avoid locale issues)
    """
    out = subprocess.check_output(
        cmd,
        cwd=str(cwd),
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return out.strip()


def test_integration_repo_tree_and_file_at_ref(tmp_git_repo: Path):
    """
    Sanity integration:
    - repo tree lists known files
    - read_file_at_ref returns content for README.md
    """
    from grounded_git_mcp.server import repo_tree_resource, read_file_resource

    tree = repo_tree_resource(root=str(tmp_git_repo), ref="HEAD")
    assert isinstance(tree, dict)
    assert "items" in tree
    assert isinstance(tree["items"], list)

    paths = {it["path"] for it in tree["items"] if isinstance(it, dict) and "path" in it}
    assert "README.md" in paths
    assert "src/app.py" in paths

    readme = read_file_resource(root=str(tmp_git_repo), ref="HEAD", path="README.md")
    assert isinstance(readme, dict)
    assert readme["path"] == "README.md"
    assert isinstance(readme["content"], str)
    assert "# dummy" in readme["content"]


def test_integration_diff_range_after_change(tmp_git_repo: Path, make_change):
    """
    Integration that requires HEAD~1:
    - create a new commit so HEAD~1 exists
    - call diff_range_resource(base=HEAD~1, head=HEAD)
    """
    from grounded_git_mcp.server import diff_range_resource

    make_change("x.txt", "hello\n")

    _run(["git", "add", "-A"], tmp_git_repo)
    _run(["git", "commit", "-m", "add x"], tmp_git_repo)

    out = diff_range_resource(root=str(tmp_git_repo), base="HEAD~1", head="HEAD")
    assert isinstance(out, dict)
    assert out["base"] == "HEAD~1"
    assert out["head"] == "HEAD"
    assert "diff" in out and isinstance(out["diff"], str)

    assert "x.txt" in out["diff"]


def test_integration_policy_enforced_even_in_integration(tmp_git_repo: Path):
    """
    Policy integration:
    SafeGitRunner must still block dangerous subcommands.
    """
    from grounded_git_mcp.core.git_runner import SafeGitRunner

    runner = SafeGitRunner(root=str(tmp_git_repo))
    with pytest.raises(GitPolicyError):
        runner.run(["push"])  


def test_integration_approval_flow_write_command(tmp_git_repo: Path, make_change):
    """
    Stage 5 integration:
    propose -> confirm -> execute for a medium-risk write command (git add -A).
    We make a working-tree change and then stage it through approval flow.
    """
    from grounded_git_mcp.server import propose_git_command_tool, execute_confirmed_tool

    make_change("stage_me.txt", "data\n")

    proposal = propose_git_command_tool(root=str(tmp_git_repo), args=["add", "-A"])
    assert isinstance(proposal, dict)
    assert "confirmation_id" in proposal
    cid = proposal["confirmation_id"]

    confirm_text = proposal.get("prompt_to_confirm") or f"I CONFIRM {cid}"

    result = execute_confirmed_tool(
        root=str(tmp_git_repo),
        confirmation_id=cid,
        user_confirmation=confirm_text,
    )

    assert isinstance(result, dict)
    assert "output" in result
    assert isinstance(result["output"], dict)

    assert result["output"].get("exit_code") == 0

    status = _run(["git", "status", "--porcelain=v1"], tmp_git_repo)
    assert "A  stage_me.txt" in status or "A  stage_me.txt".replace("/", "\\") in status
