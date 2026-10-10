"""Shared Gemini chat-model factory.

langchain-google-genai is imported lazily so the rest of the package (schemas,
utilities, API wiring) can be imported and tested without it installed.
"""
import os
from typing import Any


def get_chat_model(temperature: float = 0, **kwargs: Any):
    """Return a ChatGoogleGenerativeAI (Gemini 2.5 Flash) configured from GOOGLE_API_KEY."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Google API key is required. Please set GOOGLE_API_KEY in your .env file.")
    from langchain_google_genai import ChatGoogleGenerativeAI

    params = dict(
        model="gemini-2.5-flash",
        temperature=temperature,
        max_tokens=None,
        timeout=None,
        max_retries=2,
        google_api_key=api_key,
    )
    params.update(kwargs)
    return ChatGoogleGenerativeAI(**params)
