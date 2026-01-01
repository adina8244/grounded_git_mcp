from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(eq=False)
class GroundedGitMCPError(Exception):
    """Base error for the project."""
    message: str = ""
    context: Mapping[str, Any] | None = None

    def __str__(self) -> str:
        if not self.context:
            return self.message or self.__class__.__name__
        return f"{self.message or self.__class__.__name__} | context={dict(self.context)}"


class InvalidRootError(GroundedGitMCPError):
    """Raised when repo root is invalid or outside allowed scope."""


class GitPolicyError(GroundedGitMCPError):
    """Raised when a git command violates the security policy."""


class GitExecutionError(GroundedGitMCPError):
    """Raised when executing a git command fails."""
