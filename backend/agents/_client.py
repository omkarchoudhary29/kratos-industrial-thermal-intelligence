"""
agents/_client.py
-----------------
Provider-agnostic LLM client.

Set LLM_PROVIDER=claude (default), gemini, or huggingface in your .env.

Claude:      requires ANTHROPIC_API_KEY
Gemini:      requires GEMINI_API_KEY
Hugging Face: requires HF_TOKEN
"""

from __future__ import annotations

import os
from typing import Generator

_PROVIDER = os.environ.get("LLM_PROVIDER", "claude").lower()

# ── Claude ─────────────────────────────────────────────────────────────────────

_CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
_CLAUDE_MAX_TOKENS = 1024


def _claude_call(system: str, user_msg: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=_CLAUDE_MODEL,
        max_tokens=_CLAUDE_MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


def _claude_stream(system: str, messages: list[dict]) -> Generator[str, None, None]:
    import anthropic
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    with client.messages.stream(
        model=_CLAUDE_MODEL,
        max_tokens=_CLAUDE_MAX_TOKENS,
        system=system,
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


# ── Gemini ──────────────────────────────────────────────────────────────────────

_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
_GEMINI_FALLBACK_MODEL = os.environ.get("GEMINI_FALLBACK_MODEL", "gemini-3.6-flash")


def _gemini_call(system: str, user_msg: str) -> str:
    import logging
    import requests

    models_to_try = [_GEMINI_MODEL]
    if _GEMINI_FALLBACK_MODEL and _GEMINI_FALLBACK_MODEL != _GEMINI_MODEL:
        models_to_try.append(_GEMINI_FALLBACK_MODEL)

    last_error = None
    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
        }
        try:
            res = requests.post(
                url,
                params={"key": os.environ["GEMINI_API_KEY"]},
                json=body,
                timeout=20,
            )
            if res.ok:
                return res.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            logging.getLogger(__name__).warning("Gemini %s error %s: %s", model_name, res.status_code, res.text[:300])
            last_error = RuntimeError(f"Gemini API error ({model_name}): HTTP {res.status_code}")
        except Exception as e:
            logging.getLogger(__name__).warning("Gemini %s exception: %s", model_name, e)
            last_error = e

    raise last_error or RuntimeError("Gemini models failed to respond")


def _gemini_stream(system: str, messages: list[dict]) -> Generator[str, None, None]:
    """Stream a multi-turn Gemini chat via REST SSE with automatic fallback.

    Claude history format  → {"role": "user"|"assistant", "content": "..."}
    Gemini history format  → {"role": "user"|"model",     "parts": [{"text": "..."}]}
    """
    import json as _json
    import logging
    import requests

    contents = [
        {
            "role": "model" if m["role"] == "assistant" else "user",
            "parts": [{"text": m["content"]}],
        }
        for m in messages
    ]
    body = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": contents,
    }

    models_to_try = [_GEMINI_MODEL]
    if _GEMINI_FALLBACK_MODEL and _GEMINI_FALLBACK_MODEL != _GEMINI_MODEL:
        models_to_try.append(_GEMINI_FALLBACK_MODEL)

    streamed_any = False
    last_error = None

    for model_name in models_to_try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:streamGenerateContent"
        try:
            with requests.post(
                url,
                params={"key": os.environ["GEMINI_API_KEY"], "alt": "sse"},
                json=body,
                stream=True,
                timeout=25,
            ) as res:
                if not res.ok:
                    logging.getLogger(__name__).warning("Gemini %s stream error HTTP %s: %s", model_name, res.status_code, res.text[:300])
                    last_error = RuntimeError(f"Gemini API error ({model_name}): HTTP {res.status_code}")
                    continue

                for raw in res.iter_lines():
                    if not raw:
                        continue
                    line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(payload)
                        text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                        if text:
                            streamed_any = True
                            yield text
                    except (KeyError, IndexError, _json.JSONDecodeError):
                        continue

            if streamed_any:
                return
        except Exception as e:
            logging.getLogger(__name__).warning("Gemini %s stream exception: %s", model_name, e)
            last_error = e

    if not streamed_any:
        raise last_error or RuntimeError("All Gemini streaming models failed")


# ── Hugging Face ───────────────────────────────────────────────────────────────

_HF_MODEL = os.environ.get("HF_MODEL", "deepseek-ai/DeepSeek-V4-Flash")
_HF_API_URL = "https://router.huggingface.co/v1/chat/completions"
_HF_MAX_TOKENS = 1024


def _huggingface_messages(system: str, messages: list[dict]) -> list[dict]:
    """Return OpenAI-compatible chat messages with the system prompt first."""
    return [{"role": "system", "content": system}, *messages]


def _huggingface_call(system: str, user_msg: str) -> str:
    import logging
    import requests

    body = {
        "model": _HF_MODEL,
        "messages": _huggingface_messages(
            system, [{"role": "user", "content": user_msg}]
        ),
        "max_tokens": _HF_MAX_TOKENS,
    }
    res = requests.post(
        _HF_API_URL,
        headers={"Authorization": f"Bearer {os.environ['HF_TOKEN']}"},
        json=body,
        timeout=120,
    )
    if not res.ok:
        logging.getLogger(__name__).error(
            "Hugging Face error %s: %s", res.status_code, res.text[:500]
        )
        raise RuntimeError(f"Hugging Face API error: HTTP {res.status_code}")
    return res.json()["choices"][0]["message"]["content"].strip()


def _huggingface_stream(
    system: str, messages: list[dict]
) -> Generator[str, None, None]:
    """Stream an OpenAI-compatible chat completion through HF Inference."""
    import json as _json
    import requests

    body = {
        "model": _HF_MODEL,
        "messages": _huggingface_messages(system, messages),
        "max_tokens": _HF_MAX_TOKENS,
        "stream": True,
    }
    with requests.post(
        _HF_API_URL,
        headers={"Authorization": f"Bearer {os.environ['HF_TOKEN']}"},
        json=body,
        stream=True,
        timeout=120,
    ) as res:
        if not res.ok:
            raise RuntimeError(f"Hugging Face API error: HTTP {res.status_code}")
        for raw in res.iter_lines():
            if not raw:
                continue
            line = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload == "[DONE]":
                break
            try:
                chunk = _json.loads(payload)
                text = chunk["choices"][0]["delta"].get("content")
                if text:
                    yield text
            except (KeyError, IndexError, TypeError, _json.JSONDecodeError):
                continue


# ── Public interface ────────────────────────────────────────────────────────────

def call_llm(system: str, user_msg: str) -> str:
    """Single-turn synchronous call. Returns the response text."""
    if _PROVIDER == "gemini":
        return _gemini_call(system, user_msg)
    if _PROVIDER in {"huggingface", "hf"}:
        return _huggingface_call(system, user_msg)
    return _claude_call(system, user_msg)


def stream_llm(system: str, messages: list[dict]) -> Generator[str, None, None]:
    """Multi-turn streaming call. Yields text chunks."""
    if _PROVIDER == "gemini":
        yield from _gemini_stream(system, messages)
    elif _PROVIDER in {"huggingface", "hf"}:
        yield from _huggingface_stream(system, messages)
    else:
        yield from _claude_stream(system, messages)


def get_llm_metadata() -> dict[str, str]:
    """Return non-secret provider details for report provenance and caching."""
    if _PROVIDER == "gemini":
        return {"provider": "gemini", "model": _GEMINI_MODEL}
    if _PROVIDER in {"huggingface", "hf"}:
        return {"provider": "huggingface", "model": _HF_MODEL}
    return {"provider": "claude", "model": _CLAUDE_MODEL}
