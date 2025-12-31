from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GitRunResult:
    argv: list[str]
    root: str
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: int
    timed_out: bool
    output_truncated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "argv": self.argv,
            "root": self.root,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "duration_ms": self.duration_ms,
            "timed_out": self.timed_out,
            "output_truncated": self.output_truncated,
        }
