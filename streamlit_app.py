"""
Streamlit Frontend — Health Literacy Assistant
================================================
Alternative frontend for the application (lightweight, single-file).
Run: streamlit run streamlit_app.py
"""

import streamlit as st
import httpx

# Configuration
API_URL = "http://localhost:8003/api/v1"

# Page config
st.set_page_config(
    page_title="Health Literacy Assistant",
    layout="wide",
)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
if "current_citations" not in st.session_state:
    st.session_state.current_citations = []
if "show_clinical" not in st.session_state:
    st.session_state.show_clinical = False

# Layout: Main Chat Area + Source Sidebar
main_col, sidebar_col = st.columns([3, 1])

with main_col:
    st.title("Health Literacy Assistant")
    st.caption("Ask health questions — answers are from verified medical documents with citations.")

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Show feedback buttons for assistant messages
            if msg["role"] == "assistant" and msg.get("message_id"):
                col1, col2, col3 = st.columns([1, 1, 8])
                with col1:
                    if st.button("Helpful", key=f"up_{msg['message_id']}"):
                        try:
                            httpx.post(f"{API_URL}/feedback/", json={
                                "message_id": msg["message_id"],
                                "conversation_id": st.session_state.conversation_id or "",
                                "is_positive": True,
                                "original_question": msg.get("question", ""),
                                "ai_answer": msg["content"],
                            }, timeout=10.0)
                            st.toast("Thanks for the feedback!")
                        except Exception:
                            pass
                with col2:
                    if st.button("Not helpful", key=f"down_{msg['message_id']}"):
                        st.session_state[f"show_correction_{msg['message_id']}"] = True

                # Show correction input if thumbs down clicked
                if st.session_state.get(f"show_correction_{msg['message_id']}"):
                    correction = st.text_area(
                        "What should the correct answer be?",
                        key=f"correction_{msg['message_id']}"
                    )
                    if st.button("Submit Correction", key=f"submit_{msg['message_id']}"):
                        try:
                            httpx.post(f"{API_URL}/feedback/", json={
                                "message_id": msg["message_id"],
                                "conversation_id": st.session_state.conversation_id or "",
                                "is_positive": False,
                                "original_question": msg.get("question", ""),
                                "ai_answer": msg["content"],
                                "user_correction": correction,
                                "error_category": "wrong_information",
                            }, timeout=10.0)
                            st.toast("Correction saved to Golden Dataset")
                            st.session_state[f"show_correction_{msg['message_id']}"] = False
                        except Exception:
                            st.error("Failed to submit feedback")

    # Chat input
    if prompt := st.chat_input("Ask a health question..."):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            with st.spinner("Searching medical documents..."):
                try:
                    response = httpx.post(
                        f"{API_URL}/chat/",
                        json={
                            "message": prompt,
                            "conversation_id": st.session_state.conversation_id,
                        },
                        timeout=120.0,
                    )

                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.conversation_id = data["conversation_id"]

                        if st.session_state.show_clinical:
                            answer = data["clinical_answer"]
                        else:
                            answer = data["simplified_answer"]

                        st.markdown(answer)
                        st.session_state.current_citations = data.get("citations", [])

                        if data.get("is_emergency"):
                            st.error("Emergency detected — please contact emergency services (112/108)")

                        if data.get("pii_detected"):
                            st.warning("Personal information was detected and removed from your query.")

                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": answer,
                            "message_id": data["message"]["id"],
                            "question": prompt,
                        })
                    else:
                        st.error(f"Error: {response.status_code}")

                except httpx.ConnectError:
                    st.error("Cannot connect to API. Start the server with: uvicorn app.main:app --port 8003")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# Source Sidebar
with sidebar_col:
    st.markdown("### Source Citations")
    st.caption("Document sections used for the answer")
    st.markdown("---")

    if st.session_state.current_citations:
        for i, citation in enumerate(st.session_state.current_citations, 1):
            with st.expander(
                f"{citation['source']} — Page {citation['page_number']}",
                expanded=(i == 1)
            ):
                st.markdown(f"**Section:** {citation['section_header']}")
                st.markdown(f"**Relevance:** {citation['relevance_score']:.1%}")
                st.markdown("**Excerpt:**")
                st.info(citation['text_snippet'])
    else:
        st.markdown("*No citations yet. Ask a question to see source documents.*")

    st.markdown("---")

    # Toggle clinical vs simplified
    st.session_state.show_clinical = st.toggle(
        "Show Clinical Answer",
        value=st.session_state.show_clinical,
    )

    # New conversation
    if st.button("New Conversation"):
        st.session_state.messages = []
        st.session_state.conversation_id = None
        st.session_state.current_citations = []
        st.rerun()
