from __future__ import annotations


class GroundedGitMCPError(Exception):
    """Base error for the project."""


class InvalidRootError(GroundedGitMCPError):
    pass


class GitPolicyError(GroundedGitMCPError):
    pass


class GitExecutionError(GroundedGitMCPError):
    pass