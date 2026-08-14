# AI Agent Workbench

A proper tool-using agent, not another chatbot. Give it a task like *"Find the latest information about Tesla, calculate its market cap, and save a report"* — the agent decides which tools to call, in what order, and pauses for your approval before taking any action that writes to disk.

## Live Demo

Not yet deployed. Runs locally in a few minutes — see [Local Installation](#local-installation).

## Demo Video

Coming soon.

## Architecture

```
                  ┌── calculator        (safe AST-based arithmetic, no eval())
                  │
                  ├── web_search        (Tavily search API)
                  │
User → Agent ─────┼── query_database    (read-only SQL, isolated demo DB)
      (tool loop)  │
                  ├── http_get          (SSRF-guarded generic GET)
                  │
                  └── file_search /
                      save_report       (sandboxed workspace; save_report needs approval)
```

- **`backend/`** — FastAPI service running the agent loop: calls OpenAI with the tool schemas, executes whichever tools the model requests, retries on failure, and pauses for human approval before dangerous actions (currently: writing a report to disk)
- **`frontend/`** — Streamlit chat UI, with a live tool-execution log and an approve/reject prompt when the agent is waiting on you
- **Persistence** — SQLite by default (`./data/agent.db`), swappable for Postgres via `DATABASE_URL` with no code changes (SQLAlchemy)
- Conversation history, every tool call, and its result/error are all persisted per conversation — nothing lives only in memory

## Features

- **Tool calling** — 6 tools across 5 categories (web search, calculator, database, HTTP API, file search/save), dispatched via OpenAI's native tool-calling
- **Agent state** — each conversation tracks `active` / `awaiting_approval`, persisted in the database, not in a Python variable
- **Conversation history** — full message history (including tool calls and results) persisted per conversation and replayed to the model on every turn
- **Tool execution logs** — every tool call's arguments, status, result/error, and attempt count, visible in the UI and via `GET /conversations/{id}/logs`
- **Retry/error handling** — failed tool calls retry automatically (configurable), and failures are surfaced back to the model as a tool result instead of crashing the request
- **Human approval before dangerous actions** — `save_report` (the only tool that writes to disk) always pauses for explicit approve/reject before running

## Tech Stack

| Layer | Choice |
|---|---|
| Backend API | Python, FastAPI |
| Frontend | Streamlit |
| LLM | OpenAI (`gpt-4o-mini`, native tool calling) |
| Persistence | SQLAlchemy — SQLite by default, Postgres-ready via `DATABASE_URL` |
| Web search | Tavily search API |
| Validation | Pydantic |
| Testing | `pytest` |

## Local Installation

```bash
git clone https://github.com/Thananjayan91/ai-agent-workbench.git
cd ai-agent-workbench
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then fill in OPENAI_API_KEY and TAVILY_API_KEY
```

Run it (two terminals):

```bash
uvicorn backend.main:app --reload        # API at http://localhost:8000/docs
streamlit run frontend/streamlit_app.py  # UI at http://localhost:8501
```

Full walkthrough, including a worked example and troubleshooting, is in [docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md).

## Environment Variables

Set in `.env` (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | *(required)* | Project-scoped API key from platform.openai.com/api-keys |
| `TAVILY_API_KEY` | *(empty)* | Free-tier key from tavily.com, used by `web_search`; left blank, the tool fails gracefully instead of the app crashing |
| `CHAT_MODEL` | `gpt-4o-mini` | OpenAI model used for the agent loop |
| `DATABASE_URL` | `sqlite:///./data/agent.db` | SQLAlchemy connection string; point at Postgres for production |
| `HTTP_TOOL_ALLOWED_DOMAINS` | *(empty = any public domain)* | Comma-separated domain allowlist for the `http_get` tool |
| `MAX_AGENT_ITERATIONS` | `15` | Cap on model calls per turn, to prevent runaway tool-call loops |
| `TOOL_MAX_RETRIES` | `2` | Retries per tool call before the failure is surfaced to the model |

## API Documentation

Interactive Swagger UI is auto-generated at `http://localhost:8000/docs` once the backend is running. Main endpoints:

| Method | Path | Description |
|---|---|---|
| `GET` | `/conversations` | List all conversations |
| `POST` | `/conversations` | Create a conversation (`{"title": "..."}`) |
| `GET` | `/conversations/{id}` | Get a conversation with its full message history |
| `DELETE` | `/conversations/{id}` | Delete a conversation |
| `POST` | `/conversations/{id}/messages` | Send a message; runs the agent loop until it answers or needs approval |
| `POST` | `/conversations/{id}/approve` | Approve (`{"approve": true}`) or reject (`{"approve": false}`) a pending dangerous action |
| `GET` | `/conversations/{id}/logs` | Full tool-call log for a conversation |
| `GET` | `/health` | Liveness check |

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

34 tests covering the calculator's safe evaluator, file/HTTP/database tool safety guards (path traversal, SSRF, SQL injection), the full agent loop (tool calling, retry, approval/rejection) with OpenAI mocked, and the API end to end. Running the suite costs nothing, needs no real API key, and makes no network calls.

## Future Improvements

- Containerize with Docker (`Dockerfile` + `docker-compose.yml` covering backend, frontend, and Postgres)
- LangGraph for more complex, branching agent workflows
- Expand the approval-required set beyond `save_report` (e.g. any tool writing to an external system)
- Streaming responses instead of waiting for the full agent loop to finish
- Authentication and per-user conversation scoping
- Deploy a live demo

## Known Limitations

- **No authentication** — anyone who can reach the API can create, message, or delete any conversation
- **Single dangerous-action queue** — only one tool call can be `awaiting_approval` at a time per conversation; this is enough for the current tool set but would need revisiting if more approval-gated tools are added
- **`web_search` requires a `TAVILY_API_KEY`** — without one, the tool fails on every call; the agent still degrades gracefully (retries, then reports the error to the model instead of crashing the request)
- **No rate limiting or per-conversation request caps**

## History

`web_search` originally scraped DuckDuckGo's HTML endpoint via headless Playwright. That was dropped after confirming — from two different networks, against two different DDG endpoints — that DDG's anti-bot detection was blocking the requests outright (same anonymized error code both times), not just failing in one sandboxed environment. Swapped to the Tavily search API, which is built for this exact use case.
