"""
LLM provider adapter for dashboard chat.

The LLM is only allowed to produce text. Tool execution remains gated by
tool_registry.py and chat_router.py.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
DEFAULT_OPENAI_MODEL = "gpt-4o"
DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-6"
DEFAULT_DEEPSEEK_MODEL = "deepseek-chat"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"


class LLMProviderError(RuntimeError):
    pass


def _provider_name() -> str:
    configured = os.environ.get("CHAT_LLM_PROVIDER") or os.environ.get("AI_PROVIDER")
    if configured:
        return configured.strip().lower()
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    return "ollama"


def provider_status(probe: bool = False) -> dict[str, Any]:
    provider = _provider_name()
    status: dict[str, Any] = {
        "provider": provider,
        "available": None,
        "model": None,
        "base_url": None,
    }

    if provider == "ollama":
        base_url = _ollama_base_url()
        model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
        status.update({"base_url": base_url, "model": model})
        if probe:
            status["available"] = _probe_ollama(base_url)
    elif provider == "anthropic":
        status.update({
            "available": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "model": os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL),
        })
    elif provider == "openai":
        status.update({
            "available": bool(os.environ.get("OPENAI_API_KEY")),
            "model": os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        })
    elif provider == "deepseek":
        status.update({
            "available": bool(os.environ.get("DEEPSEEK_API_KEY")),
            "model": os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
            "base_url": DEEPSEEK_BASE_URL,
        })
    else:
        status["available"] = False

    return status


def complete_json(system: str, user: str, max_tokens: int = 600) -> str:
    return _complete(system, user, max_tokens, json_mode=True)


def complete_text(system: str, user: str, max_tokens: int = 1000) -> str:
    return _complete(system, user, max_tokens, json_mode=False)


def _complete(system: str, user: str, max_tokens: int, json_mode: bool) -> str:
    provider = _provider_name()
    if provider == "ollama":
        return _complete_ollama(system, user, max_tokens, json_mode)
    if provider == "anthropic":
        return _complete_anthropic(system, user, max_tokens)
    if provider == "openai":
        return _complete_openai(system, user, max_tokens, json_mode)
    if provider == "deepseek":
        return _complete_deepseek(system, user, max_tokens, json_mode)
    raise LLMProviderError(
        "Unsupported CHAT_LLM_PROVIDER. Use 'ollama', 'openai', 'anthropic', or 'deepseek'."
    )


def _ollama_base_url() -> str:
    return os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL).rstrip("/")


def _probe_ollama(base_url: str) -> bool:
    try:
        req = urllib.request.Request(f"{base_url}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return 200 <= resp.status < 300
    except (OSError, urllib.error.URLError):
        return False


def _complete_ollama(system: str, user: str, max_tokens: int, json_mode: bool) -> str:
    base_url = _ollama_base_url()
    model = os.environ.get("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL).strip()
    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "temperature": 0,
            "num_predict": max_tokens,
        },
    }
    if json_mode:
        payload["format"] = "json"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise LLMProviderError(
            f"Ollama is not reachable at {base_url}. Start Ollama or change OLLAMA_BASE_URL."
        ) from exc
    except json.JSONDecodeError as exc:
        raise LLMProviderError("Ollama returned a non-JSON HTTP response.") from exc

    message = body.get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise LLMProviderError("Ollama response did not contain message.content.")
    return content.strip()


def _complete_anthropic(system: str, user: str, max_tokens: int) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMProviderError("ANTHROPIC_API_KEY is not configured.")

    import anthropic as _anthropic

    client = _anthropic.Anthropic(api_key=api_key)
    resp = client.messages.create(
        model=os.environ.get("ANTHROPIC_MODEL", DEFAULT_ANTHROPIC_MODEL),
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return resp.content[0].text.strip()


def _complete_openai(system: str, user: str, max_tokens: int, json_mode: bool) -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise LLMProviderError("OPENAI_API_KEY is not configured.")

    import openai as _openai

    client = _openai.OpenAI(api_key=api_key)
    kwargs: dict[str, Any] = {
        "model": os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content.strip()


def _complete_deepseek(system: str, user: str, max_tokens: int, json_mode: bool) -> str:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise LLMProviderError("DEEPSEEK_API_KEY is not configured.")

    import openai as _openai

    client = _openai.OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    kwargs: dict[str, Any] = {
        "model": os.environ.get("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content.strip()
