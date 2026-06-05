import json
import os

import httpx
from openai import OpenAI

BUSY = "Sorry, I'm having a brief issue on my end. Could you try that again in a moment?"

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Ordered fallback chain — all Llama 3.3 70B so the persona stays consistent across providers.
# Cerebras first (fastest, best for <2s voice). Each is used only if its key is set.
CHAIN = [
    ("cerebras", "https://api.cerebras.ai/v1", "CEREBRAS_API_KEY", "CEREBRAS_MODEL", "llama-3.3-70b"),
    ("groq", "https://api.groq.com/openai/v1", "GROQ_API_KEY", "GROQ_MODEL", "llama-3.3-70b-versatile"),
    ("sambanova", "https://api.sambanova.ai/v1", "SAMBANOVA_API_KEY", "SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct"),
    ("openrouter", "https://openrouter.ai/api/v1", "OPENROUTER_API_KEY", "OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
]

_clients = {}


def _oai(name, base, key_env):
    key = os.getenv(key_env)
    if not key:
        return None
    if name not in _clients:
        _clients[name] = OpenAI(base_url=base, api_key=key)
    return _clients[name]


def providers():
    out = []
    for name, base, key_env, model_env, default_model in CHAIN:
        client = _oai(name, base, key_env)
        if client:
            out.append((client, os.getenv(model_env, default_model)))
    return out


def _gemini(messages, temperature):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("all providers exhausted and no GEMINI_API_KEY")
    contents, system = [], ""
    for m in messages:
        if m["role"] == "system":
            system += (m.get("content") or "") + "\n"
        elif m.get("content"):
            role = "user" if m["role"] in ("user", "tool") else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={key}"
    body = {"contents": contents, "generationConfig": {"temperature": temperature}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    r = httpx.post(url, json=body, timeout=40)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def complete(messages, temperature=0.3, max_tokens=1024):
    for client, model in providers():
        try:
            r = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, max_tokens=max_tokens
            )
            return r.choices[0].message.content
        except Exception:
            continue
    try:
        return _gemini(messages, temperature)
    except Exception:
        return ""


def respond(messages, tools=None, handlers=None, temperature=0.3):
    if tools and handlers:
        yield _tool_loop(messages, tools, handlers, temperature)
    else:
        yield from _stream(messages, temperature)


def _stream(messages, temperature):
    for client, model in providers():
        try:
            stream = client.chat.completions.create(
                model=model, messages=messages, temperature=temperature, stream=True
            )
            produced = False
            for chunk in stream:
                c = chunk.choices[0].delta.content
                if c:
                    produced = True
                    yield c
            if produced:
                return
        except Exception:
            continue
    try:
        yield _gemini(messages, temperature)
    except Exception:
        yield BUSY


def _tool_loop(messages, tools, handlers, temperature, depth=0):
    for client, model in providers():
        try:
            msg = client.chat.completions.create(
                model=model, messages=messages, tools=tools, temperature=temperature
            ).choices[0].message
            if not msg.tool_calls:
                return msg.content or ""
            messages = messages + [{
                "role": "assistant", "content": msg.content,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in msg.tool_calls
                ],
            }]
            for tc in msg.tool_calls:
                result = handlers[tc.function.name](json.loads(tc.function.arguments or "{}"))
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})
            if depth >= 4:
                return msg.content or ""
            return _tool_loop(messages, tools, handlers, temperature, depth + 1)
        except Exception:
            continue
    try:
        return _gemini(messages, temperature)
    except Exception:
        return BUSY
