"""mh-mind Streamlit UI — chat with your notes."""

import streamlit as st

from mh_mind.artifacts import save_transcript
from mh_mind.chat import ChatResponse, answer
from mh_mind.llm import Message

st.set_page_config(page_title="mh-mind", layout="wide")
st.title("mh-mind")
st.caption("Chat with your notes.")

# --- Temperature label mapping ---
_CREATIVITY_LABELS = {
    0.0: "Precise",
    0.3: "Balanced",
    0.7: "Creative",
    1.0: "Adventurous",
    1.5: "Wild",
    2.0: "Unhinged",
}
_CREATIVITY_BREAKPOINTS = sorted(_CREATIVITY_LABELS.keys())


def _get_creativity_label(temp: float) -> str:
    """Return the descriptive label for the nearest lower breakpoint."""
    label_key = _CREATIVITY_BREAKPOINTS[0]
    for bp in _CREATIVITY_BREAKPOINTS:
        if bp <= temp:
            label_key = bp
        else:
            break
    return _CREATIVITY_LABELS[label_key]


# --- Sidebar controls ---
with st.sidebar:
    scope = st.radio(
        "Search scope",
        options=["both", "notes", "docs"],
        format_func=lambda s: {
            "both": "Both",
            "notes": "Apple Notes",
            "docs": "Word docs",
        }[s],
        index=0,
    )
    temperature = st.slider(
        "Creativity level",
        min_value=0.0,
        max_value=2.0,
        value=0.3,
        step=0.1,
    )
    st.caption(f"**{_get_creativity_label(temperature)}** ({temperature:.1f})")
    st.divider()
    if st.button("New conversation"):
        st.session_state.messages = []
        st.session_state.transcript = []
        st.rerun()

# --- Session state ---
if "messages" not in st.session_state:
    st.session_state.messages = []  # list of {"role": ..., "content": ...}
if "transcript" not in st.session_state:
    st.session_state.transcript = []  # list of (query, ChatResponse)

# --- Display chat history ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show expandable citations for assistant messages
        if msg["role"] == "assistant" and "sources" in msg:
            for src in msg["sources"]:
                title = src.metadata.get("title", "Untitled")
                date = src.metadata.get("created", src.metadata.get("modified", ""))
                source_type = "Apple Note" if src.source == "notes" else "Word doc"
                excerpt = src.text[:300]

                with st.expander(f"[{src.number}] {source_type}: {title} ({date})"):
                    st.markdown(f"> {excerpt}")

# --- Handle new input ---
if prompt := st.chat_input("Ask a question about your notes"):
    # Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Build conversation history for multi-turn context
    history = [
        Message(role=m["role"], content=m["content"])
        for m in st.session_state.messages[:-1]  # exclude the current query
        if m["role"] in ("user", "assistant")
    ]

    # Get the answer
    with st.chat_message("assistant"):
        with st.spinner("Searching your notes..."):
            response: ChatResponse = answer(prompt, scope=scope, conversation_history=history, temperature=temperature)

        st.markdown(response.answer)

        # Expandable citations
        if response.sources:
            for src in response.sources:
                title = src.metadata.get("title", "Untitled")
                date = src.metadata.get("created", src.metadata.get("modified", ""))
                source_type = "Apple Note" if src.source == "notes" else "Word doc"
                excerpt = src.text[:300]

                with st.expander(f"[{src.number}] {source_type}: {title} ({date})"):
                    st.markdown(f"> {excerpt}")

    # Store in session state
    st.session_state.messages.append({
        "role": "assistant",
        "content": response.answer,
        "sources": response.sources,
    })
    st.session_state.transcript.append((prompt, response))

    # Auto-save artifact after each response
    topic = prompt[:60]
    artifact_path = save_transcript(
        st.session_state.transcript,
        topic=topic,
        scope=scope,
    )
    st.sidebar.caption(f"Saved to `{artifact_path.name}`")
