from __future__ import annotations

import pytest


def test_parse_status_porcelain_basic():
    from grounded_git_mcp.core.parsers import parse_status_porcelain

    raw = "\n".join(
        [
            " M README.md",
            "A  src/new.py",
            "?? notes.txt",
        ]
    )

    out = parse_status_porcelain(raw.splitlines())

    assert isinstance(out, list)
    assert len(out) == 3

    assert out[0].path == "README.md"
    assert out[0].xy == " M"          

    assert out[1].path == "src/new.py"
    assert out[1].xy == "A "          

    assert out[2].path == "notes.txt"
    assert out[2].xy == "??"          


def test_parse_status_porcelain_rename_parses_orig_path():
    from grounded_git_mcp.core.parsers import parse_status_porcelain

    raw = "R  old_name.txt -> new_name.txt"
    out = parse_status_porcelain([raw])

    assert len(out) == 1
    assert out[0].xy == "R "
    assert out[0].path == "new_name.txt"
    assert out[0].orig_path == "old_name.txt"


def test_parse_status_porcelain_ignores_empty_lines():
    from grounded_git_mcp.core.parsers import parse_status_porcelain

    out = parse_status_porcelain(["", " M a.txt", ""])
    assert len(out) == 1
    assert out[0].path == "a.txt"
    assert out[0].xy == " M"
