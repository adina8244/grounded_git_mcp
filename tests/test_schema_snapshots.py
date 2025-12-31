from __future__ import annotations

from typing import Any

import pytest


def assert_schema(obj: Any, schema: Any, path: str = "$") -> None:
    """
    A tiny schema matcher that is *stable*:
    - schema can be: type (e.g. str), dict of schemas, list schema (single element = item schema), or callable predicate.
    """
    if isinstance(schema, type):
        assert isinstance(obj, schema), f"{path}: expected {schema.__name__}, got {type(obj).__name__}"
        return

    if callable(schema) and not isinstance(schema, dict):
        assert schema(obj), f"{path}: predicate failed for value={obj!r}"
        return

    if isinstance(schema, dict):
        assert isinstance(obj, dict), f"{path}: expected dict, got {type(obj).__name__}"
        for k, subschema in schema.items():
            assert k in obj, f"{path}: missing key '{k}'"
            assert_schema(obj[k], subschema, f"{path}.{k}")
        return

    if isinstance(schema, list):
        assert isinstance(obj, list), f"{path}: expected list, got {type(obj).__name__}"
        if len(schema) == 0:
            return
        item_schema = schema[0]
        for i, item in enumerate(obj):
            assert_schema(item, item_schema, f"{path}[{i}]")
        return

    raise TypeError(f"Unsupported schema type at {path}: {schema!r}")


@pytest.mark.parametrize("resource_name", ["repo_tree", "diff_range", "read_file"])
def test_resources_return_stable_schema(resource_name, tmp_git_repo, git_head):
    """
    Snapshot-style schema tests:
    - ensures contract for resources stays stable
    - does NOT pin volatile values (hashes, timestamps)
    """
    from grounded_git_mcp.server import repo_tree_resource, diff_range_resource, read_file_resource

    if resource_name == "repo_tree":
        out = repo_tree_resource(root=str(tmp_git_repo), ref="HEAD")
        assert_schema(out, {
            "root": str,
            "ref": str,
            "items": [ 
                {
                    "path": str,
                }
            ],
            "truncated": bool,
            "git": dict,
        })

    elif resource_name == "diff_range":
        # diff between HEAD~0..HEAD is usually empty; we assert schema only.
        out = diff_range_resource(root=str(tmp_git_repo), base="HEAD~0", head="HEAD")
        assert_schema(out, {
            "root": str,
            "base": str,
            "head": str,
            "diff": str,
            "truncated": bool,
            "git": dict,
        })

    elif resource_name == "read_file":
        out = read_file_resource(root=str(tmp_git_repo), ref="HEAD", path="README.md")
        assert_schema(out, {
            "root": str,
            "ref": str,
            "path": str,
            "content": str,
            "truncated": bool,
            "line_count": int,
            "git": dict,
        })


def test_tools_output_schema_is_stable(tmp_git_repo):
    """
    Schema snapshot for tool output.
    In your codebase the tool is status_porcelain (and wrapper status_porcelain_tool in server.py).
    """
    from grounded_git_mcp.tools.git_tools import status_porcelain

    out = status_porcelain(root=str(tmp_git_repo), max_entries=200)
    assert_schema(out, {
        "count": int,
        "entries": [dict],  
        "git": dict,
    })
