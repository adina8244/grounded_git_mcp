from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from grounded_git_mcp.tools import (
    blame,
    detect_conflicts,
    diff_summary,
    grep,
    log,
    repo_info,
    show_commit,
    status_porcelain,
)

mcp = FastMCP("grounded-git-mcp")


@mcp.tool()
def repo_info_tool(root: str = ".") -> dict:
    return repo_info(root=root)


@mcp.tool()
def status_porcelain_tool(root: str = ".", max_entries: int = 200) -> dict:
    return status_porcelain(root=root, max_entries=max_entries)


@mcp.tool()
def diff_summary_tool(root: str = ".", staged: bool = False, against: str | None = None) -> dict:
    return diff_summary(root=root, staged=staged, against=against)


@mcp.tool()
def log_tool(root: str = ".", n: int = 20) -> dict:
    return log(root=root, n=n)


@mcp.tool()
def show_commit_tool(commit: str, root: str = ".", patch: bool = True) -> dict:
    return show_commit(commit=commit, root=root, patch=patch)


@mcp.tool()
def grep_tool(pattern: str, root: str = ".", pathspec: str | None = None, ignore_case: bool = False) -> dict:
    return grep(pattern=pattern, root=root, pathspec=pathspec, ignore_case=ignore_case)


@mcp.tool()
def blame_tool(file_path: str, root: str = ".", start_line: int = 1, end_line: int = 200) -> dict:
    return blame(file_path=file_path, root=root, start_line=start_line, end_line=end_line)


@mcp.tool()
def detect_conflicts_tool(root: str = ".") -> dict:
    return detect_conflicts(root=root)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
