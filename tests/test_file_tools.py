import pytest

from backend.tools.file_tools import UnsafeFilenameError, file_search, save_report


def test_save_report_writes_file():
    result = save_report("note.txt", "hello world")
    assert result["filename"] == "note.txt"
    assert result["bytes_written"] == len("hello world".encode("utf-8"))


def test_file_search_finds_saved_content():
    save_report("alpha.txt", "The quick brown fox jumps over the lazy dog")
    matches = file_search("brown fox")
    assert len(matches) == 1
    assert matches[0]["filename"] == "alpha.txt"
    assert "brown fox" in matches[0]["snippet"]


def test_file_search_no_match_returns_empty():
    save_report("beta.txt", "nothing relevant here")
    assert file_search("nonexistent-phrase-xyz") == []


def test_save_report_rejects_path_traversal():
    with pytest.raises(UnsafeFilenameError):
        save_report("../../evil.txt", "malicious")


def test_save_report_rejects_disallowed_extension():
    with pytest.raises(UnsafeFilenameError):
        save_report("script.py", "print('hi')")


def test_save_report_rejects_absolute_path():
    with pytest.raises(UnsafeFilenameError):
        save_report("/etc/passwd", "malicious")
