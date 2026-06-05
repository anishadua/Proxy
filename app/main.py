import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from app import llm, persona, tools
from app.rag import Retriever

STATIC = Path(__file__).resolve().parent / "static"

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

state = {"retriever": None, "started": time.time()}


@app.on_event("startup")
def load():
    try:
        state["retriever"] = Retriever()
    except Exception as e:
        print(f"Retriever not ready: {e}")


def booking_tools():
    if os.getenv("CALCOM_API_KEY") and os.getenv("CALCOM_EVENT_TYPE_ID"):
        return tools.TOOLS, tools.HANDLERS
    return None, None


EMPTY_RETRIEVAL = {"results": [], "top_score": 0.0, "confident": False}


def answer(history, channel):
    query = next((m["content"] for m in reversed(history) if m["role"] == "user"), "")
    tool_defs, handlers = booking_tools()
    booking = bool(tool_defs) and persona.is_booking_intent(query)
    retrieval = EMPTY_RETRIEVAL if booking else state["retriever"].retrieve(query)
    msgs = persona.build_messages(history, channel, retrieval, booking=booking)
    if booking:
        return llm.respond(msgs, tools=tool_defs, handlers=handlers)
    return llm.respond(msgs)


@app.get("/health")
def health():
    r = state["retriever"]
    return {
        "status": "ok",
        "uptime_s": round(time.time() - state["started"]),
        "chunks": len(r.store.meta) if r else 0,
        "booking": bool(booking_tools()[0]),
    }


@app.get("/")
def home():
    return FileResponse(STATIC / "index.html")


@app.post("/api/chat")
async def api_chat(req: Request):
    body = await req.json()
    history = body.get("messages") or [{"role": "user", "content": body.get("message", "")}]
    if state["retriever"] is None:
        return JSONResponse({"error": "knowledge base not loaded"}, status_code=503)

    def gen():
        for delta in answer(history, "chat"):
            yield delta

    return StreamingResponse(gen(), media_type="text/plain")


@app.post("/v1/chat/completions")
async def completions(req: Request):
    body = await req.json()
    history = [m for m in body.get("messages", []) if m.get("role") != "system"]
    stream = body.get("stream", True)
    if state["retriever"] is None:
        return JSONResponse({"error": "knowledge base not loaded"}, status_code=503)

    if not stream:
        text = "".join(answer(history, "voice"))
        return {
            "id": f"chatcmpl-{int(time.time())}",
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
        }

    def sse():
        cid = f"chatcmpl-{int(time.time())}"
        head = {"id": cid, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"role": "assistant"}}]}
        yield f"data: {json.dumps(head)}\n\n"
        for delta in answer(history, "voice"):
            chunk = {"id": cid, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {"content": delta}}]}
            yield f"data: {json.dumps(chunk)}\n\n"
        tail = {"id": cid, "object": "chat.completion.chunk", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
        yield f"data: {json.dumps(tail)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")
