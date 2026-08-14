import requests

from backend.config import settings

_TAVILY_URL = "https://api.tavily.com/search"


class WebSearchError(RuntimeError):
    pass


def web_search(query: str, max_results: int = 5) -> list[dict]:
    max_results = max(1, min(max_results, 10))
    try:
        response = requests.post(
            _TAVILY_URL,
            json={
                "api_key": settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
            },
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise WebSearchError(f"Tavily search request failed: {e}") from e

    data = response.json()
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("content", ""),
        }
        for r in data.get("results", [])[:max_results]
    ]


SCHEMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web and return titles, URLs, and snippets for the top results.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "description": "1-10, default 5"},
            },
            "required": ["query"],
        },
    },
}


def execute(query: str, max_results: int = 5) -> dict:
    return {"query": query, "results": web_search(query, max_results)}
