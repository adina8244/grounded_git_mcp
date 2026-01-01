from __future__ import annotations

import pytest
from pathlib import Path

from grounded_git_mcp.core.errors import GitPolicyError


def _git(cmd: list[str], cwd: Path) -> str:
    import subprocess
    return subprocess.check_output(
        cmd,
        cwd=str(cwd),
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    ).strip()


def _status(cwd: Path) -> str:
    return _git(["git", "status", "--porcelain"], cwd)


def test_approval_flow_happy_path_add_file(tmp_git_repo: Path, make_change):
    """
    propose -> execute works for a write command (git add -A).
    """
    from grounded_git_mcp.server import propose_git_command_tool, execute_confirmed_tool

    # create an untracked file
    make_change("new.txt", "content\n")
    assert "?? new.txt" in _status(tmp_git_repo)

    proposal = propose_git_command_tool(
        root=str(tmp_git_repo),
        args=["add", "-A"],
    )
    assert "confirmation_id" in proposal
    cid = proposal["confirmation_id"]

    # sanity: should be classified as write
    assert proposal["classification"]["kind"] in ("write", "read")
    assert proposal["classification"]["kind"] == "write"

    res = execute_confirmed_tool(
        root=str(tmp_git_repo),
        confirmation_id=cid,
        user_confirmation=f"I CONFIRM {cid}",
    )

    assert "output" in res and "exit_code" in res["output"]
    assert res["output"]["exit_code"] == 0

    # file should be staged -> porcelain shows "A  new.txt" (or "AM"/etc depending)
    s = _status(tmp_git_repo)
    assert "A  new.txt" in s or "A  new.txt".replace("/", "\\") in s or "A  new.txt".replace("\\", "/") in s


def test_approval_flow_wrong_phrase_rejected(tmp_git_repo: Path, make_change):
    from grounded_git_mcp.server import propose_git_command_tool, execute_confirmed_tool

    make_change("x.txt", "data\n")
    proposal = propose_git_command_tool(root=str(tmp_git_repo), args=["add", "-A"])
    cid = proposal["confirmation_id"]

    with pytest.raises(ValueError):
        execute_confirmed_tool(
            root=str(tmp_git_repo),
            confirmation_id=cid,
            user_confirmation="WRONG PHRASE",
        )


def test_approval_flow_unknown_id_rejected(tmp_git_repo: Path):
    from grounded_git_mcp.server import execute_confirmed_tool

    with pytest.raises(ValueError):
        execute_confirmed_tool(
            root=str(tmp_git_repo),
            confirmation_id="does-not-exist",
            user_confirmation="I CONFIRM does-not-exist",
        )


def test_approval_flow_replay_attack_prevented(tmp_git_repo: Path, make_change):
    from grounded_git_mcp.server import propose_git_command_tool, execute_confirmed_tool

    make_change("replay.txt", "v1\n")
    proposal = propose_git_command_tool(root=str(tmp_git_repo), args=["add", "-A"])
    cid = proposal["confirmation_id"]

    # first time succeeds
    execute_confirmed_tool(
        root=str(tmp_git_repo),
        confirmation_id=cid,
        user_confirmation=f"I CONFIRM {cid}",
    )

    # second time must fail (one-time token)
    with pytest.raises(ValueError):
        execute_confirmed_tool(
            root=str(tmp_git_repo),
            confirmation_id=cid,
            user_confirmation=f"I CONFIRM {cid}",
        )


def test_approval_flow_head_changed_precondition(tmp_git_repo: Path, make_change):
    """
    Your propose stores expected_head internally (per your earlier design).
    If HEAD changes after propose, execute should fail.
    """
    from grounded_git_mcp.server import propose_git_command_tool, execute_confirmed_tool

    make_change("headchange.txt", "v1\n")
    proposal = propose_git_command_tool(root=str(tmp_git_repo), args=["add", "-A"])
    cid = proposal["confirmation_id"]

    # Change HEAD: commit something else
    make_change("other.txt", "other\n")
    _git(["git", "add", "-A"], tmp_git_repo)
    _git(["git", "commit", "-m", "move head"], tmp_git_repo)

    with pytest.raises(ValueError):
        execute_confirmed_tool(
            root=str(tmp_git_repo),
            confirmation_id=cid,
            user_confirmation=f"I CONFIRM {cid}",
        )


@pytest.mark.parametrize("args", [["push", "--force"], ["reset", "--hard"], ["clean", "-fd"]])
def test_dangerous_commands_rejected_at_proposal(tmp_git_repo: Path, args):
    """
    Critical-risk commands must be rejected already at propose stage.
    Depending on your implementation it may raise GitPolicyError or ValueError.
    """
    from grounded_git_mcp.server import propose_git_command_tool

    with pytest.raises((GitPolicyError, ValueError)):
        propose_git_command_tool(root=str(tmp_git_repo), args=args)
