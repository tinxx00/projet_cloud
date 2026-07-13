"""LLM gateway: OpenAI, Anthropic, Groq.

This module centralizes API calls so the UI page stays clean.
"""
from __future__ import annotations

import os
from typing import Any

import requests


class LLMError(Exception):
    pass


def _post(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int = 45) -> dict[str, Any]:
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if resp.status_code >= 400:
        raise LLMError(f"HTTP {resp.status_code}: {resp.text[:300]}")
    return resp.json()


def has_api_key(provider: str) -> bool:
    provider = provider.lower()
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    if provider == "anthropic":
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    if provider == "groq":
        return bool(os.getenv("GROQ_API_KEY"))
    return False


def generate_reply(
    provider: str,
    messages: list[dict[str, str]],
    system_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 500,
) -> str:
    """Generate a reply from the selected provider."""
    provider = provider.lower()
    history = [{"role": m["role"], "content": m["content"]} for m in messages][-12:]

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            raise LLMError("OPENAI_API_KEY manquante")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}] + history,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = _post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            payload=payload,
        )
        return data["choices"][0]["message"]["content"].strip()

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY manquante")
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        payload = {
            "model": model,
            "system": system_prompt,
            "messages": history,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = _post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            payload=payload,
        )
        parts = data.get("content", [])
        text = "\n".join(p.get("text", "") for p in parts if p.get("type") == "text").strip()
        return text or "Je n'ai pas pu générer de réponse."

    if provider == "groq":
        api_key = os.getenv("GROQ_API_KEY", "")
        if not api_key:
            raise LLMError("GROQ_API_KEY manquante")
        model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        payload = {
            "model": model,
            "messages": [{"role": "system", "content": system_prompt}] + history,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = _post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            payload=payload,
        )
        return data["choices"][0]["message"]["content"].strip()

    raise LLMError(f"Provider non supporté: {provider}")
