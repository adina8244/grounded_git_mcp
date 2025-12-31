from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from grounded_git_mcp.core.confirmations import (
    Confirmation,
    FileConfirmationStore,
    Preconditions,
    command_hash,
    new_confirmation_id,
)
from grounded_git_mcp.core.classification import classify_git_args
from grounded_git_mcp.core.git_runner import SafeGitRunner, require_ok
from grounded_git_mcp.core.errors import GitExecutionError, GitPolicyError


_CONFIRM_TTL_SECONDS = 30 * 60 


def _require_ok(ok: bool, msg: str) -> None:
    if not ok:
        raise ValueError(msg)


def _repo_path(root: str) -> Path:
    return Path(root).resolve()


def _git_stdout(runner: SafeGitRunner, args: list[str], *, context: str, read_only: bool) -> str:
    res = runner.run(args, read_only=read_only)
    require_ok(res, context=context)
    return (res.stdout or "").strip()


def _check_preconditions(runner: SafeGitRunner, p: Preconditions) -> None:
    if p.expected_branch:
        branch = _git_stdout(
            runner,
            ["rev-parse", "--abbrev-ref", "HEAD"],
            context="precondition(branch)",
            read_only=True,
        )
        _require_ok(branch == p.expected_branch, f"Branch changed: expected {p.expected_branch}, got {branch}")

    if p.expected_head:
        head = _git_stdout(
            runner,
            ["rev-parse", "HEAD"],
            context="precondition(head)",
            read_only=True,
        )
        _require_ok(head == p.expected_head, "HEAD changed since approval.")

    if p.require_clean:
        st = _git_stdout(
            runner,
            ["status", "--porcelain"],
            context="precondition(clean)",
            read_only=True,
        )
        _require_ok(st == "", "Working tree is not clean.")

    if p.require_no_conflicts:
        unmerged = _git_stdout(
            runner,
            ["diff", "--name-only", "--diff-filter=U"],
            context="precondition(conflicts)",
            read_only=True,
        )
        _require_ok(unmerged == "", "Unmerged/conflicted files detected.")


def propose_git_command(
    *,
    root: str = ".",
    args: list[str],
    expected_branch: str | None = None,
    require_clean: bool = False,
) -> dict[str, Any]:
    """
    Create a one-time approval token for a specific git command.
    The command is NOT executed here.
    """
    root_path = _repo_path(root)
    runner = SafeGitRunner(root_path)  
    store = FileConfirmationStore(root_path)

    classification = classify_git_args(args)
    _require_ok(classification["risk"] != "critical", f"Command rejected: {classification['reason']}")

    expected_head = _git_stdout(
        runner,
        ["rev-parse", "HEAD"],
        context="propose(expected_head)",
        read_only=True,
    )

    cid = new_confirmation_id(root_path, args)
    now = int(time.time())

    c = Confirmation(
        confirmation_id=cid,
        root=str(root_path),
        args=args,
        classification=classification,
        cmd_hash=command_hash(args),
        created_at=now,
        expires_at=now + _CONFIRM_TTL_SECONDS,
        max_uses=1,
        used=0,
        preconditions=Preconditions(
            expected_head=expected_head,
            expected_branch=expected_branch,
            require_clean=require_clean,
            require_no_conflicts=True,
        ),
    )
    store.put(c)

    return {
        "summary": "Proposal created. Requires explicit confirmation to execute.",
        "confirmation_id": cid,
        "classification": classification,
        "args": args,
        "expires_at": c.expires_at,
        "preconditions": {
            "expected_head": c.preconditions.expected_head,
            "expected_branch": c.preconditions.expected_branch,
            "require_clean": c.preconditions.require_clean,
            "require_no_conflicts": c.preconditions.require_no_conflicts,
        },
        "prompt_to_confirm": f"I CONFIRM {cid}",
        "notes": [
            "Token is one-time and expires automatically.",
            "Execution fails if HEAD/branch changed or conflicts exist (per preconditions).",
        ],
    }


def execute_confirmed(
    *,
    root: str = ".",
    confirmation_id: str,
    user_confirmation: str,
) -> dict[str, Any]:
    """
    Execute the exact previously proposed command only after explicit user confirmation.
    """
    root_path = _repo_path(root)
    runner = SafeGitRunner(root_path) 
    store = FileConfirmationStore(root_path)

    c = store.get(confirmation_id)
    _require_ok(c is not None, "Unknown confirmation_id.")
    _require_ok(c.root == str(root_path), "Token repo_root mismatch.")
    _require_ok(c.can_use(), "Token expired or already used.")

    expected_phrase = f"I CONFIRM {confirmation_id}"
    _require_ok(user_confirmation.strip() == expected_phrase, f"Invalid confirmation phrase. Use: {expected_phrase}")

    _require_ok(command_hash(c.args) == c.cmd_hash, "Command hash mismatch (tampering detected).")

    _check_preconditions(runner, c.preconditions)

    res = runner.run(c.args, read_only=False)
    require_ok(res, context="execute_confirmed(run)")

    result = {
        "summary": "Executed confirmed git command.",
        "confirmation_id": confirmation_id,
        "classification": c.classification,
        "args": c.args,
        "output": {
            "stdout": res.stdout,
            "stderr": res.stderr,
            "exit_code": res.exit_code,
            "duration_ms": res.duration_ms,
            "timed_out": res.timed_out,
            "output_truncated": res.output_truncated,
        },
    }
    store.mark_used(c, result=result)
    return result
