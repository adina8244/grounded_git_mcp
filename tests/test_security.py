from __future__ import annotations

from pathlib import Path
import pytest

from grounded_git_mcp.core.errors import InvalidRootError
from grounded_git_mcp.core.security import resolve_root, ensure_within_root


def test_resolve_root_with_valid_directory(tmp_path: Path):
    result = resolve_root(tmp_path)
    assert result == tmp_path.resolve()
    assert result.is_dir()


def test_resolve_root_with_nonexistent_path(tmp_path: Path):
    fake_path = tmp_path / "does_not_exist"
    with pytest.raises(InvalidRootError, match="Root does not exist:"):
        resolve_root(fake_path)


def test_resolve_root_with_file_instead_of_directory(tmp_path: Path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("data", encoding="utf-8")
    with pytest.raises(InvalidRootError, match="Root is not a directory:"):
        resolve_root(file_path)


def test_resolve_root_expands_user_home(tmp_path: Path, monkeypatch):
    # We only verify that expanduser() is called and result is absolute.
    # This avoids depending on the real OS home folder.
    monkeypatch.setattr(Path, "expanduser", lambda self: tmp_path if str(self) == "~" else self)
    result = resolve_root("~")
    assert result.is_absolute()
    assert result == tmp_path.resolve()


def test_ensure_within_root_allows_valid_subpath(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()
    subdir = root / "subdir"
    subdir.mkdir()

    result = ensure_within_root(root, subdir)
    assert result == subdir.resolve()


def test_ensure_within_root_blocks_path_traversal_with_dotdot(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()

    malicious = root / ".." / ".." / "etc" / "passwd"
    with pytest.raises(InvalidRootError, match="Path escapes root"):
        ensure_within_root(root, malicious)


def test_ensure_within_root_blocks_absolute_path_outside_root(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(InvalidRootError, match="Path escapes root"):
        ensure_within_root(root, outside)


def test_ensure_within_root_allows_root_itself(tmp_path: Path):
    root = tmp_path
    result = ensure_within_root(root, root)
    assert result == root.resolve()


def test_ensure_within_root_normalizes_paths(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()

    subdir = root / "subdir"
    subdir.mkdir()

    # Still inside root after normalization
    weird_path = root / "subdir" / "." / ".." / "subdir"
    result = ensure_within_root(root, weird_path)
    assert result == subdir.resolve()


def test_ensure_within_root_handles_symlinks_correctly(tmp_path: Path):
    root = tmp_path / "repo"
    root.mkdir()

    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.txt"
    secret.write_text("secret data", encoding="utf-8")

    link = root / "link"
    try:
        link.symlink_to(secret)
    except OSError:
        pytest.skip("Symlinks not supported or not permitted on this system")

    with pytest.raises(InvalidRootError, match="Path escapes root"):
        ensure_within_root(root, link)
