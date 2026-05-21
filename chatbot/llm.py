"""Groq LLM configuration via LangChain."""

import logging
import os
from typing import Iterator

from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llama-3.3-70b-versatile"
LEGACY_MODEL = "llama3-70b-8192"
FALLBACK_MODEL = "llama-3.3-70b-versatile"


def get_api_key() -> str:
    """Get API key from Streamlit secrets or environment."""
    try:
        import streamlit as st
        if hasattr(st, 'secrets') and 'GROQ_API_KEY' in st.secrets:
            return st.secrets['GROQ_API_KEY']
    except (ImportError, Exception):
        pass
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GROQ_API_KEY is not set. Add it to Streamlit Cloud secrets or your .env file."
        )
    return api_key


def get_groq_model_name() -> str:
    return os.getenv("GROQ_MODEL", DEFAULT_MODEL)


def create_llm(streaming: bool = True, temperature: float = 0.3) -> ChatGroq:
    """Instantiate ChatGroq with API key from environment."""
    api_key = get_api_key()
    model = get_groq_model_name()
    logger.info("Initializing Groq LLM: %s (streaming=%s)", model, streaming)
    return ChatGroq(
        groq_api_key=api_key,
        model_name=model,
        temperature=temperature,
        streaming=streaming,
        max_tokens=4096,
    )


def invoke_with_fallback(llm: ChatGroq, messages: list) -> str:
    """Invoke LLM; retry with fallback model if primary is deprecated."""
    try:
        response = llm.invoke(messages)
        return response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        err = str(exc).lower()
        if "decommissioned" in err or "not found" in err or "model" in err:
            logger.warning("Primary model failed, trying fallback: %s", exc)
            fallback = ChatGroq(
                groq_api_key=get_api_key(),
                model_name=FALLBACK_MODEL,
                temperature=llm.temperature,
                streaming=False,
                max_tokens=4096,
            )
            response = fallback.invoke(messages)
            return response.content if hasattr(response, "content") else str(response)
        raise


def stream_llm_response(
    llm: ChatGroq,
    system_prompt: str,
    question: str,
    chat_history: list[tuple[str, str]] | None = None,
) -> Iterator[str]:
    """Stream tokens from Groq for a single turn."""
    messages = [SystemMessage(content=system_prompt)]
    if chat_history:
        for human, ai in chat_history:
            messages.append(HumanMessage(content=human))
            messages.append(AIMessage(content=ai))
    messages.append(HumanMessage(content=question))

    try:
        for chunk in llm.stream(messages):
            if chunk.content:
                yield chunk.content
    except Exception as exc:
        err = str(exc).lower()
        if "decommissioned" in err or "not found" in err:
            logger.warning("Streaming failed on primary model, using fallback.")
            fallback = ChatGroq(
                groq_api_key=get_api_key(),
                model_name=FALLBACK_MODEL,
                temperature=0.3,
                streaming=True,
                max_tokens=4096,
            )
            for chunk in fallback.stream(messages):
                if chunk.content:
                    yield chunk.content
        else:
            raise
