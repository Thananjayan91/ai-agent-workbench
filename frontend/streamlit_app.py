import requests
import streamlit as st

API_URL = "http://localhost:8000"

st.set_page_config(page_title="AI Agent Workbench", page_icon="🤖")
st.title("🤖 AI Agent Workbench")


def fetch_conversations():
    response = requests.get(f"{API_URL}/conversations", timeout=5)
    return response.json() if response.ok else []


with st.sidebar:
    st.header("Conversation")

    try:
        conversations = fetch_conversations()
    except requests.exceptions.RequestException:
        st.error(
            f"Can't reach the API at {API_URL}. Is `uvicorn backend.main:app --reload` "
            "running in another terminal?"
        )
        st.stop()

    with st.expander("+ New conversation"):
        new_title = st.text_input("Title", value="New conversation", key="new_conversation_title")
        if st.button("Create"):
            response = requests.post(f"{API_URL}/conversations", json={"title": new_title}, timeout=5)
            if response.ok:
                st.rerun()
            else:
                st.error(response.json().get("detail", "Failed to create conversation"))

    if not conversations:
        st.info("Create a conversation above to get started.")
        st.stop()

    labels = [f"#{c['id']} {c['title']}" for c in conversations]
    selected_label = st.selectbox("Active conversation", labels)
    selected_id = conversations[labels.index(selected_label)]["id"]

    if st.button("Delete conversation"):
        requests.delete(f"{API_URL}/conversations/{selected_id}", timeout=5)
        st.rerun()

    st.divider()
    st.caption(
        "Tools: calculator, web_search, query_database, http_get, file_search, save_report "
        "(save_report requires your approval before it runs)."
    )

response = requests.get(f"{API_URL}/conversations/{selected_id}", timeout=5)
conversation = response.json()

for message in conversation["messages"]:
    if message["role"] in ("user", "assistant") and message["content"]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

if conversation["status"] == "awaiting_approval":
    logs = requests.get(f"{API_URL}/conversations/{selected_id}/logs", timeout=5).json()
    pending = next((log for log in logs if log["status"] == "pending_approval"), None)
    if pending:
        st.warning(
            f"**Approval needed:** the agent wants to run `{pending['tool_name']}` "
            f"with arguments `{pending['arguments']}`. Allow it to proceed?"
        )
        approve_col, reject_col = st.columns(2)
        with approve_col:
            if st.button("Approve", type="primary"):
                with st.spinner("Running approved action..."):
                    requests.post(
                        f"{API_URL}/conversations/{selected_id}/approve",
                        json={"approve": True},
                        timeout=120,
                    )
                st.rerun()
        with reject_col:
            if st.button("Reject"):
                with st.spinner("Recording rejection..."):
                    requests.post(
                        f"{API_URL}/conversations/{selected_id}/approve",
                        json={"approve": False},
                        timeout=120,
                    )
                st.rerun()
else:
    prompt = st.chat_input("Ask the agent to do something...")
    if prompt:
        with st.spinner("Agent is working..."):
            response = requests.post(
                f"{API_URL}/conversations/{selected_id}/messages",
                json={"content": prompt},
                timeout=120,
            )
        if not response.ok:
            st.error(response.json().get("detail", "Request failed"))
        st.rerun()

with st.expander("Tool execution log"):
    logs = requests.get(f"{API_URL}/conversations/{selected_id}/logs", timeout=5).json()
    if not logs:
        st.caption("No tool calls yet.")
    for log in logs:
        icon = {"success": "✅", "error": "❌", "rejected": "🚫", "pending_approval": "⏳"}.get(
            log["status"], "•"
        )
        st.markdown(f"{icon} `{log['tool_name']}` — {log['status']} (attempts: {log['attempts']})")
        st.caption(f"args: {log['arguments']}")
        if log["result"]:
            st.caption(f"result: {log['result']}")
        if log["error"]:
            st.caption(f"error: {log['error']}")
