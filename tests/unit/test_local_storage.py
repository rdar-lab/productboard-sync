import pytest
from productboard_sync.storage.local import LocalStorageBackend


def test_write_creates_parent_dirs(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    backend.write_file("subdir/file.csv", "a,b\n1,2\n")
    assert (tmp_path / "subdir" / "file.csv").exists()


def test_write_overwrites_existing(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    backend.write_file("file.csv", "old content")
    backend.write_file("file.csv", "new content")
    assert (tmp_path / "file.csv").read_text() == "new content"


def test_read_returns_content(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    backend.write_file("file.csv", "hello")
    assert backend.read_file("file.csv") == "hello"


def test_read_raises_for_missing(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    with pytest.raises(FileNotFoundError):
        backend.read_file("missing.csv")


def test_list_files_returns_relative_paths(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    backend.write_file("a.csv", "")
    backend.write_file("b.csv", "")
    files = backend.list_files()
    assert set(files) == {"a.csv", "b.csv"}


def test_delete_removes_file(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    backend.write_file("file.csv", "data")
    backend.delete_file("file.csv")
    assert not (tmp_path / "file.csv").exists()


def test_delete_silent_if_missing(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    backend.delete_file("nonexistent.csv")


def test_path_traversal_write_raises(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    with pytest.raises(ValueError, match="Path traversal"):
        backend.write_file("../../etc/passwd", "bad")


def test_path_traversal_read_raises(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    with pytest.raises(ValueError, match="Path traversal"):
        backend.read_file("../../etc/passwd")


def test_path_traversal_delete_raises(tmp_path):
    backend = LocalStorageBackend(tmp_path)
    with pytest.raises(ValueError, match="Path traversal"):
        backend.delete_file("../../etc/passwd")
