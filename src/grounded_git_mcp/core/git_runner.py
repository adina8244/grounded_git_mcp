from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .errors import GitExecutionError, GitPolicyError
from .models import GitRunResult
from .security import resolve_root


def _kill_process_tree_windows(pid: int) -> None:
    """
    Kill a process tree on Windows (git may spawn helper processes such as
    credential managers, ssh, pagers, etc.).
    """
    subprocess.run(
        ["taskkill", "/PID", str(pid), "/T", "/F"],
        capture_output=True,
        text=True,
    )


def _kill_process_group_posix(p: subprocess.Popen) -> None:
    """
    Kill entire process group on POSIX when start_new_session=True.
    Fallbacks to p.kill() if group kill fails.
    """
    try:
        os.killpg(p.pid, signal.SIGKILL)
    except Exception:
        try:
            p.kill()
        except Exception:
            pass


def require_ok(res: GitRunResult, context: str) -> GitRunResult:
    if res.exit_code != 0:
        raise GitExecutionError(f"{context} failed: {res.stderr.strip()}")
    return res


@dataclass(frozen=True)
class GitRunnerConfig:
    """
    Safe runner configuration.
    """
    timeout_s: float = 3.0
    max_output_chars: int = 80_000

    # Read-only allowlist: prevents accidental destructive commands.
    read_only_allowlist: tuple[str, ...] = (
        "rev-parse",
        "status",
        "log",
        "diff",
        "show",
        "branch",
        "remote",
        "config",
        "ls-files",
        "cat-file",
        "describe",
        "tag",
        "grep",
        "blame",
        "ls-tree",
         "merge-base",
    )

class SafeGitRunner:
    """
    Safe, local-only git runner:
      - No shell
      - Enforces cwd=root
      - Timeout (hard)
      - Kills stuck process trees (Windows) / process groups (POSIX)
      - Output ceiling (stdout+stderr) with deterministic truncation
      - Standardized result: stdout/stderr/exit_code/duration_ms (+ flags)
    """

    def __init__(self, root: str | Path, config: GitRunnerConfig | None = None) -> None:
        self.root = resolve_root(root)
        self.config = config or GitRunnerConfig()

    def run(
        self,
        args: Iterable[str],
        *,
        read_only: bool = True,
        env: dict[str, str] | None = None,
    ) -> GitRunResult:
        args_list = list(args)
        self._validate_args(args_list, read_only=read_only)

        argv = ["git", *args_list]
        merged_env = self._build_env(env)

        start = time.perf_counter()
        stdout, stderr, exit_code, timed_out = self._run_process(
            argv=argv,
            cwd=self.root,
            env=merged_env,
            timeout_s=self.config.timeout_s,
        )
        duration_ms = int((time.perf_counter() - start) * 1000)

        stdout, stderr, output_truncated = self._apply_output_ceiling(stdout, stderr)

        return GitRunResult(
            argv=argv,
            root=str(self.root),
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration_ms,
            timed_out=timed_out,
            output_truncated=output_truncated,
        )

    def _validate_args(self, args_list: list[str], *, read_only: bool) -> None:
        if not args_list:
            raise GitPolicyError("Empty git args are not allowed.")

        if not read_only:
            return
        args = [a.strip() for a in args_list]
        lowered = [a.lower() for a in args]
        subcmd = lowered[0]
        if subcmd not in self.config.read_only_allowlist:
            raise GitPolicyError(
                f"Blocked git subcommand in read-only mode: '{subcmd}'. "
                f"Allowed: {', '.join(self.config.read_only_allowlist)}"
            )

        dangerous_flags = {
            "--global", "--system",  
            "--unset", "--unset-all", "--add", "--replace-all",
            "--delete",              
            "--force", "-f",         
        }

        if any(f in lowered for f in dangerous_flags):
            raise GitPolicyError(f"Blocked potentially mutating git flags in read-only mode: {args_list}")

        if subcmd == "branch" and any(t in lowered for t in {"-d", "-D".lower(), "--delete"}):
            raise GitPolicyError("Blocked branch deletion in read-only mode.")

        if subcmd == "tag" and any(t in lowered for t in {"-d", "--delete"}):
            raise GitPolicyError("Blocked tag deletion in read-only mode.")

        if subcmd == "remote" and len(lowered) >= 2:
            op = lowered[1]
            if op in {"set-url", "add", "remove", "rename"}:
                raise GitPolicyError("Blocked remote mutation in read-only mode.")

       
        if subcmd == "config":
            if len(lowered) >= 3:
                raise GitPolicyError("Blocked config write in read-only mode.")



    def _build_env(self, extra_env: dict[str, str] | None) -> dict[str, str]:
        """
        Build a controlled environment that prevents interactive hangs.
        """
        merged_env = dict(os.environ)
        merged_env.update(
            {
                "GIT_TERMINAL_PROMPT": "0",
                "GCM_INTERACTIVE": "Never",  
                "GIT_PAGER": "cat",          
                "LC_ALL": "C",
                "GIT_OPTIONAL_LOCKS": "0",

            }
        )

        if extra_env:
            merged_env.update(extra_env)

        return merged_env


    def _run_process(
        self,
        *,
        argv: list[str],
        cwd: Path,
        env: dict[str, str],
        timeout_s: float,
    ) -> tuple[str, str, int, bool]:
        """
        Run a command safely using Popen + communicate(timeout) to guarantee:
          - hard timeout
          - deterministic cleanup of stuck processes
        Returns: (stdout, stderr, exit_code, timed_out)
        """
        # POSIX: allow killing full process group
        popen_kwargs: dict = {}
        if os.name != "nt":
            popen_kwargs["start_new_session"] = True

        try:
            p = subprocess.Popen(
                argv,
                cwd=str(cwd),
                env=env,
                stdin=subprocess.DEVNULL,  
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                **popen_kwargs,
            )
        except FileNotFoundError as e:
            # git binary not found
            raise GitExecutionError("git executable not found in PATH.") from e
        except Exception as e:
            raise GitExecutionError(f"Failed to spawn git: {type(e).__name__}: {e}") from e

        timed_out = False
        try:
            out, err = p.communicate(timeout=timeout_s)
            stdout = out or ""
            stderr = err or ""
            exit_code = int(p.returncode or 0)
            return stdout, stderr, exit_code, timed_out

        except subprocess.TimeoutExpired:
            timed_out = True

            try:
                out, err = p.communicate(timeout=0.2)
            except Exception:
                out, err = ("", "")

            stdout = out or ""
            stderr = err or ""
            exit_code = 124 

            # Hard cleanup
            try:
                if os.name == "nt":
                    _kill_process_tree_windows(p.pid)
                else:
                    _kill_process_group_posix(p)
            finally:
                try:
                    p.wait(timeout=0.5)
                except Exception:
                    pass

            return stdout, stderr, exit_code, timed_out

        except Exception as e:
            # Ensure process is not left running
            try:
                if os.name == "nt":
                    _kill_process_tree_windows(p.pid)
                else:
                    _kill_process_group_posix(p)
            except Exception:
                pass
            raise GitExecutionError(f"Failed while running git: {type(e).__name__}: {e}") from e

    def _apply_output_ceiling(self, stdout: str, stderr: str) -> tuple[str, str, bool]:
        """
        Enforce output ceiling (stdout+stderr). Prefer keeping stderr.
        Deterministic truncation: keep up to half for stderr, rest for stdout.
        """
        max_chars = max(1, int(self.config.max_output_chars))
        combined_len = len(stdout) + len(stderr)
        output_truncated = combined_len > max_chars

        if not output_truncated:
            return stdout, stderr, False

        keep_stderr = min(len(stderr), max_chars // 2)
        keep_stdout = max_chars - keep_stderr

        stderr = stderr[:keep_stderr]
        stdout = stdout[:keep_stdout]

        return stdout, stderr, True
