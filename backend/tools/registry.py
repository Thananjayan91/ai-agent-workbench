from dataclasses import dataclass
from typing import Callable

from backend.tools import calculator, database, file_tools, http_api, web_search


@dataclass
class ToolSpec:
    schema: dict
    execute: Callable[..., dict]
    requires_approval: bool = False


TOOLS: dict[str, ToolSpec] = {
    "calculator": ToolSpec(calculator.SCHEMA, calculator.execute, requires_approval=False),
    "web_search": ToolSpec(web_search.SCHEMA, web_search.execute, requires_approval=False),
    "query_database": ToolSpec(database.SCHEMA, database.execute, requires_approval=False),
    "http_get": ToolSpec(http_api.SCHEMA, http_api.execute, requires_approval=False),
    "file_search": ToolSpec(
        file_tools.FILE_SEARCH_SCHEMA, file_tools.execute_file_search, requires_approval=False
    ),
    "save_report": ToolSpec(
        file_tools.SAVE_REPORT_SCHEMA, file_tools.execute_save_report, requires_approval=True
    ),
}


def tool_schemas() -> list[dict]:
    return [spec.schema for spec in TOOLS.values()]


def requires_approval(tool_name: str) -> bool:
    return TOOLS[tool_name].requires_approval


def run_tool(tool_name: str, arguments: dict) -> dict:
    if tool_name not in TOOLS:
        raise KeyError(f"Unknown tool: {tool_name}")
    return TOOLS[tool_name].execute(**arguments)
