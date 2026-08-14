from pathlib import Path

WORKSPACE_DIR = Path("data/workspace")
_ALLOWED_SUFFIXES = {".txt", ".md"}
_SNIPPET_RADIUS = 120


class UnsafeFilenameError(ValueError):
    pass


def _safe_path(filename: str) -> Path:
    if "/" in filename or "\\" in filename or ".." in filename:
        raise UnsafeFilenameError(f"Filename must not contain path separators: {filename!r}")
    name = filename.strip()
    if not name:
        raise UnsafeFilenameError("Filename must not be empty")
    if Path(name).suffix.lower() not in _ALLOWED_SUFFIXES:
        raise UnsafeFilenameError(f"Only {sorted(_ALLOWED_SUFFIXES)} files are allowed")

    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    resolved = (WORKSPACE_DIR / name).resolve()
    if resolved.parent != WORKSPACE_DIR.resolve():
        raise UnsafeFilenameError(f"Path escapes workspace: {filename!r}")
    return resolved


def file_search(query: str) -> list[dict]:
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    query_lower = query.lower()
    results = []
    for path in sorted(WORKSPACE_DIR.iterdir()):
        if not path.is_file() or path.suffix.lower() not in _ALLOWED_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        idx = text.lower().find(query_lower)
        if idx == -1:
            continue
        start = max(0, idx - _SNIPPET_RADIUS)
        end = min(len(text), idx + len(query) + _SNIPPET_RADIUS)
        results.append({"filename": path.name, "snippet": text[start:end].strip()})
    return results


def save_report(filename: str, content: str) -> dict:
    path = _safe_path(filename)
    path.write_text(content, encoding="utf-8")
    return {"filename": path.name, "bytes_written": len(content.encode("utf-8"))}


FILE_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "file_search",
        "description": "Search saved report files in the workspace for a keyword or phrase.",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
}

SAVE_REPORT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "save_report",
        "description": "Save a report to the workspace as a .txt or .md file. This writes to disk, so it requires human approval before running.",
        "parameters": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "e.g. 'tesla_report.md'"},
                "content": {"type": "string"},
            },
            "required": ["filename", "content"],
        },
    },
}


def execute_file_search(query: str) -> dict:
    return {"query": query, "matches": file_search(query)}


def execute_save_report(filename: str, content: str) -> dict:
    return save_report(filename, content)
