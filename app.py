import streamlit as st

st.set_page_config(page_title="mh-mind", layout="wide")
st.title("mh-mind")
st.caption("Chat with your notes.")

scope = st.radio(
    "Search scope",
    options=["both", "notes", "docs"],
    format_func=lambda s: {"both": "Both", "notes": "Apple Notes", "docs": "Word docs"}[s],
    horizontal=True,
    index=0,
)

if prompt := st.chat_input("Ask a question about your notes"):
    with st.chat_message("user"):
        st.write(prompt)
    with st.chat_message("assistant"):
        st.write(f"(scaffold) scope={scope} — chat pipeline not yet implemented.")
