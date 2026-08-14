# How to Run

## 1. First-time setup

```bash
cd ai-agent-workbench
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Open `.env` and set:
- `OPENAI_API_KEY` to a project-scoped key from https://platform.openai.com/api-keys
- `TAVILY_API_KEY` to a free key from https://tavily.com (1000 searches/month free tier), used by the `web_search` tool

No Docker or Postgres setup needed — the app uses SQLite by default, stored in `./data/agent.db`. Leaving `TAVILY_API_KEY` blank is fine — every other tool still works, only `web_search` will fail (gracefully; the agent reports the error and continues).

## 2. Start the app (two terminals)

**Terminal 1 — API:**
```bash
.venv\Scripts\activate
uvicorn backend.main:app --reload
```
Runs at http://localhost:8000 (Swagger docs at http://localhost:8000/docs).

**Terminal 2 — UI:**
```bash
.venv\Scripts\activate
streamlit run frontend/streamlit_app.py
```
Opens at http://localhost:8501.

## 3. Use it

1. In the sidebar, expand **+ New conversation**, give it a title, and click **Create**.
2. Type a request in the chat box, e.g.:
   > Find the latest information about Tesla, calculate its market cap in USD using shares_outstanding from the database, and save a report.
3. Watch the agent call tools — each call appears in the **Tool execution log** expander with its arguments, status, and result.
4. When the agent tries to call `save_report`, execution pauses and the sidebar shows an **Approval needed** prompt. Click **Approve** to let it write the file, or **Reject** to deny it — the agent sees your decision and continues.

## Troubleshooting

- **`AuthenticationError` / `not_authorized_invalid_key_type`** — the key in `.env` isn't a valid project API key. Generate one at platform.openai.com/api-keys with a project selected.
- **`web_search` errors with "Tavily search request failed"** — check `TAVILY_API_KEY` is set in `.env` and the backend was restarted after adding it (env vars are read once at startup).
- **Nothing happens after sending a message** — check the API terminal for errors; agent runs can take a few seconds if multiple tools are chained (web search, then calculation, then a save).
- **Stuck on "Approval needed" with no way to unblock** — click Approve or Reject in the sidebar; the conversation won't accept new messages until that specific tool call is resolved.
- **`Unsafe query` / `Unsafe filename` / `Unsafe URL` errors from a tool** — these are the tools' own safety guards (read-only SQL, workspace-sandboxed file writes, no private/internal HTTP targets) rejecting an unsafe request; this is expected behavior, not a bug.
- **Port already in use** — another process is on 8000 or 8501; stop it or run with `--port <other-port>`.
