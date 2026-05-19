"""
Resume AI Interview Chatbot — Premium futuristic Streamlit UI.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st
from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from chatbot.chains import InterviewChainManager
from chatbot.memory import get_chat_history_tuples
from ui.components import (
    inject_premium_theme,
    render_background_fx,
    render_empty_state,
    render_futuristic_header,
    render_sidebar_brand,
    render_suggestions_header,
    render_typing_indicator,
    render_upload_success_flash,
    render_upload_zone_hint,
)
from utils.helpers import (
    ensure_directories,
    extract_candidate_name,
    format_chat_for_download,
    read_resume_file,
    save_uploaded_file,
    setup_logging,
)

setup_logging()
ensure_directories()

st.set_page_config(
    page_title="InterviewCoach AI",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_premium_theme()
render_background_fx()

DEFAULT_SUGGESTIONS = [
    "Tell me about yourself",
    "Why are you changing jobs?",
    "Describe a challenging situation you handled",
    "What are your greatest strengths?",
    "Walk me through your most recent role",
]

# st.chat_message only accepts valid emojis or presets; "✦" is not a valid emoji.
USER_CHAT_AVATAR = "🧑‍💼"
ASSISTANT_CHAT_AVATAR = "✨"


def init_session_state() -> None:
    defaults = {
        "messages": [],
        "resume_loaded": False,
        "resume_text": "",
        "candidate_name": "Candidate",
        "chain_manager": None,
        "suggested_questions": DEFAULT_SUGGESTIONS,
        "interview_prep": "",
        "pending_question": None,
        "show_upload_flash": False,
        "indexing_resume": False,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def get_chain_manager() -> InterviewChainManager:
    if st.session_state.chain_manager is None:
        st.session_state.chain_manager = InterviewChainManager()
    return st.session_state.chain_manager


def process_resume_upload(uploaded_file) -> None:
    if st.session_state.get("indexing_resume"):
        st.warning("Resume indexing is already in progress. Please wait.")
        return

    try:
        st.session_state.indexing_resume = True
        with st.spinner("Neural indexing in progress…"):
            content = uploaded_file.read()
            resume_text = read_resume_file(uploaded_file.name, content)
            save_uploaded_file(uploaded_file.name, content)
            candidate_name = extract_candidate_name(resume_text)

            old_manager = st.session_state.chain_manager
            if old_manager is not None:
                old_manager.vector_store.clear()

            st.session_state.chain_manager = InterviewChainManager()
            manager = st.session_state.chain_manager
            manager.index_resume(resume_text, candidate_name)

            st.session_state.resume_text = resume_text
            st.session_state.candidate_name = candidate_name
            st.session_state.resume_loaded = True
            st.session_state.messages = []
            st.session_state.interview_prep = ""
            st.session_state.show_upload_flash = True

            try:
                st.session_state.suggested_questions = (
                    manager.generate_suggested_questions().strip().split("\n")
                )
            except Exception:
                st.session_state.suggested_questions = DEFAULT_SUGGESTIONS

        st.toast(f"Resume indexed for {candidate_name}", icon="✅")
        st.rerun()
    except Exception as exc:
        st.error(f"Could not process resume: {exc}")
    finally:
        st.session_state.indexing_resume = False


def render_sidebar() -> None:
    with st.sidebar:
        render_sidebar_brand()
        render_upload_zone_hint()

        uploaded = st.file_uploader(
            "Select file",
            type=["pdf", "docx"],
            label_visibility="collapsed",
            key="resume_uploader",
        )
        if uploaded is not None:
            if st.button("⚡ Index Resume", type="primary", use_container_width=True):
                process_resume_upload(uploaded)

        st.markdown('<div class="sidebar-section">', unsafe_allow_html=True)
        st.markdown("**Quick actions**")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Clear", use_container_width=True):
                st.session_state.messages = []
                st.rerun()
        with c2:
            if st.button("Reset", use_container_width=True):
                st.session_state.messages = []
                st.session_state.resume_loaded = False
                st.session_state.resume_text = ""
                st.session_state.chain_manager = InterviewChainManager()
                st.rerun()

        if st.session_state.resume_loaded:
            if st.button("📋 Interview Prep Guide", use_container_width=True):
                try:
                    with st.spinner("Generating prep…"):
                        st.session_state.interview_prep = (
                            get_chain_manager().generate_interview_prep()
                        )
                except Exception as exc:
                    st.error(str(exc))

            if st.session_state.interview_prep:
                with st.expander("Prep guide", expanded=False):
                    st.markdown(st.session_state.interview_prep)

        st.markdown("</div>", unsafe_allow_html=True)

        import os
        st.caption(f"Model · `{os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')}`")


def render_suggestions() -> None:
    if not st.session_state.resume_loaded:
        return
    render_suggestions_header()
    st.markdown('<div class="suggestions-wrap">', unsafe_allow_html=True)
    questions = st.session_state.suggested_questions[:8]
    cols = st.columns(2)
    for i, q in enumerate(questions):
        clean = q.strip().lstrip("0123456789.) ")
        if not clean:
            continue
        with cols[i % 2]:
            if st.button(clean, key=f"suggest_{i}", use_container_width=True):
                st.session_state.pending_question = clean
                st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def render_chat_history() -> None:
    st.markdown('<div class="chat-area">', unsafe_allow_html=True)
    for msg in st.session_state.messages:
        avatar = USER_CHAT_AVATAR if msg["role"] == "user" else ASSISTANT_CHAT_AVATAR
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
    st.markdown("</div>", unsafe_allow_html=True)


def stream_assistant_response(question: str) -> str:
    manager = get_chain_manager()
    history = get_chat_history_tuples(st.session_state.messages[:-1])

    with st.chat_message("assistant", avatar=ASSISTANT_CHAT_AVATAR):
        placeholder = st.empty()
        placeholder.markdown(render_typing_indicator(), unsafe_allow_html=True)
        full_response = ""
        try:
            chunks = manager.ask_stream(question, history)
            full_response = st.write_stream(chunks)
        except Exception as exc:
            st.error(f"AI error: {exc}")
            full_response = (
                "I could not generate a response. Please check your Groq API key."
            )
            placeholder.markdown(full_response)
        if not full_response:
            full_response = "Please try rephrasing your question."
    return full_response


def handle_user_message(question: str) -> None:
    if not st.session_state.resume_loaded:
        st.warning("Upload and index your resume in the sidebar first.")
        return
    st.session_state.messages.append({"role": "user", "content": question})
    answer = stream_assistant_response(question)
    st.session_state.messages.append({"role": "assistant", "content": answer})


def main() -> None:
    init_session_state()
    render_sidebar()

    render_futuristic_header(
        st.session_state.candidate_name,
        st.session_state.resume_loaded,
    )

    if st.session_state.show_upload_flash:
        render_upload_success_flash()
        st.session_state.show_upload_flash = False

    render_suggestions()

    if not st.session_state.messages and st.session_state.resume_loaded:
        render_empty_state()

    render_chat_history()

    if st.session_state.pending_question:
        q = st.session_state.pending_question
        st.session_state.pending_question = None
        handle_user_message(q)
        st.rerun()

    placeholder = (
        "Ask anything about your experience…"
        if st.session_state.resume_loaded
        else "Index your resume to unlock the chat…"
    )
    if prompt := st.chat_input(placeholder, disabled=not st.session_state.resume_loaded):
        handle_user_message(prompt)
        st.rerun()

    if st.session_state.messages:
        st.markdown('<div class="footer-actions">', unsafe_allow_html=True)
        text = format_chat_for_download(
            st.session_state.messages,
            st.session_state.candidate_name,
        )
        st.download_button(
            label="⬇ Download conversation",
            data=text,
            file_name=f"interview_{st.session_state.candidate_name.replace(' ', '_')}.txt",
            mime="text/plain",
            use_container_width=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
