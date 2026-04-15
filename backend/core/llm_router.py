# -*- coding: utf-8 -*-
"""
core/llm_router.py — единый интерфейс к LLM-провайдерам.

Провайдеры:
  1. DeepSeekProvider  — DeepSeek API (env: DEEPSEEK_API_KEY)
  2. OpenAIProvider    — OpenAI GPT API (env: OPENAI_API_KEY)  [stub]
  3. AnthropicProvider — Anthropic Claude API (env: ANTHROPIC_API_KEY)  [stub]
  4. GeminiProvider    — Google Gemini API (env: GEMINI_API_KEY)  [stub]
  5. OllamaProvider    — локальный Ollama (env: OLLAMA_URL, OLLAMA_MODEL)

Fallback-политика: выбранный провайдер → Ollama → ошибка.

Использование:
    from core.llm_router import chat_completion
    reply = await chat_completion(messages, provider="deepseek")

ТИТАН-5.
"""

import os
from typing import Optional

import httpx

# ───────────────────────────────────────────────────────────────────────
# Конфигурация из переменных окружения
# ───────────────────────────────────────────────────────────────────────

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/chat/completions")
DEEPSEEK_MODEL = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-haiku-4-5")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_API_URL_TMPL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-exp")

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:4b")


# ───────────────────────────────────────────────────────────────────────
# Провайдеры
# ───────────────────────────────────────────────────────────────────────

async def _call_deepseek(messages: list[dict], **kwargs) -> str:
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("DEEPSEEK_API_KEY не задан")
    headers = {"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": kwargs.get('model', DEEPSEEK_MODEL),
        "messages": messages,
        "max_tokens": kwargs.get('max_tokens', 1500),
        "temperature": kwargs.get('temperature', 0.3),
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(DEEPSEEK_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_openai(messages: list[dict], **kwargs) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY не задан")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": kwargs.get('model', OPENAI_MODEL),
        "messages": messages,
        "max_tokens": kwargs.get('max_tokens', 1500),
        "temperature": kwargs.get('temperature', 0.3),
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(OPENAI_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


async def _call_anthropic(messages: list[dict], **kwargs) -> str:
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY не задан")
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    # Anthropic выделяет system отдельно от messages
    system_content = ""
    clean_messages = []
    for m in messages:
        if m["role"] == "system":
            system_content += m["content"] + "\n"
        else:
            clean_messages.append(m)
    payload = {
        "model": kwargs.get('model', ANTHROPIC_MODEL),
        "messages": clean_messages,
        "max_tokens": kwargs.get('max_tokens', 1500),
        "temperature": kwargs.get('temperature', 0.3),
    }
    if system_content:
        payload["system"] = system_content
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(ANTHROPIC_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"]


async def _call_gemini(messages: list[dict], **kwargs) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY не задан")
    model = kwargs.get('model', GEMINI_MODEL)
    url = GEMINI_API_URL_TMPL.format(model=model) + f"?key={GEMINI_API_KEY}"
    # Gemini: system — отдельно, messages — list of {role, parts:[{text}]}
    system_content = ""
    contents = []
    for m in messages:
        if m["role"] == "system":
            system_content += m["content"] + "\n"
            continue
        role = "model" if m["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    payload = {"contents": contents}
    if system_content:
        payload["systemInstruction"] = {"parts": [{"text": system_content}]}
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_ollama(messages: list[dict], **kwargs) -> str:
    payload = {
        "model": kwargs.get('model', OLLAMA_MODEL),
        "messages": messages,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(OLLAMA_URL, json=payload)
        resp.raise_for_status()
        return resp.json().get("message", {}).get("content", "")


PROVIDERS = {
    "deepseek": _call_deepseek,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "gemini": _call_gemini,
    "ollama": _call_ollama,
}


# ───────────────────────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────────────────────

def available_providers() -> dict:
    """Какие провайдеры сейчас имеют ключи / доступны."""
    return {
        "deepseek": bool(DEEPSEEK_API_KEY),
        "openai": bool(OPENAI_API_KEY),
        "anthropic": bool(ANTHROPIC_API_KEY),
        "gemini": bool(GEMINI_API_KEY),
        "ollama": True,  # Ollama локальная — проверяется живым запросом
    }


async def chat_completion(messages: list[dict], provider: Optional[str] = None,
                            fallback: bool = True, **kwargs) -> str:
    """Запросить ответ у LLM.

    provider: 'deepseek' | 'openai' | 'anthropic' | 'gemini' | 'ollama'.
              Если None — выбираем первый доступный (deepseek > openai > anthropic > gemini > ollama).
    fallback: при ошибке выбранного → пробуем Ollama как резерв.
    """
    # Автовыбор: первый с ключом
    if provider is None:
        avail = available_providers()
        for p in ("deepseek", "openai", "anthropic", "gemini", "ollama"):
            if avail.get(p):
                provider = p
                break
        if provider is None:
            raise RuntimeError("Нет доступных LLM-провайдеров. Задайте API-ключ в .env или запустите Ollama.")

    func = PROVIDERS.get(provider)
    if not func:
        raise RuntimeError(f"Неизвестный провайдер: {provider}")

    try:
        return await func(messages, **kwargs)
    except Exception as e:
        if fallback and provider != "ollama":
            try:
                return await _call_ollama(messages, **kwargs)
            except Exception as e2:
                raise RuntimeError(f"Провайдер {provider} упал: {e}. Резерв (Ollama) тоже: {e2}")
        raise


async def check_status() -> dict:
    """Статус всех провайдеров для UI."""
    status = available_providers().copy()
    # Проверяем Ollama живым запросом
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.get(OLLAMA_URL.replace('/api/chat', '/api/tags'))
        status["ollama"] = True
    except Exception:
        status["ollama"] = False
    status["default"] = next(
        (p for p in ("deepseek", "openai", "anthropic", "gemini", "ollama") if status.get(p)),
        None,
    )
    return status
