# Proxy — an AI persona of Anisha Dua

A callable and chattable AI representative of Anisha, grounded over her real resume and GitHub repos.
It answers questions about her background and projects, stays honest under probing, and books a real
interview on her calendar with no human in the loop.

- **Chat:** https://proxy-ok1d.onrender.com
- **Voice:** +16626578854

One FastAPI backend powers both surfaces, so the voice agent and the chat answer from the same
retrieval and the same guardrails — no hardcoded replies.

## Architecture

```
   resume.pdf + interview notes ─┐
   github.com/anishadua repos  ──┤   scrub (PII/internal) → chunk → local embed (bge-small)
   (README, code, commits)       │            │
                                  └────────────┴──────────────► data/  (local vector store)
                                                                     │
        VAPI  ──POST /v1/chat/completions (SSE)──►  FastAPI backend (app/)
     phone # / Deepgram / barge-in                  • tiered retrieval + confidence gate
                                                     • gpt-oss-120b (Cerebras), Llama 3.3 70B failover
        Browser ──POST /api/chat──►                  • booking tools → Cal.com v2
                                                     • /health (kept warm by cron-job.org)
                                                              │
                                                     Cal.com ─┘  real slots + confirmed booking
```

**Retrieval.** Documents are tagged in tiers — tier 1 (resume, READMEs, design notes, repo summary
cards), tier 2 (commit messages), tier 3 (source code). Normal questions search tiers 1–2; tier 3 is
only pulled in when the question is about code. A confidence gate flags low-similarity retrievals as a
backstop; refusal of unknown or adversarial questions is enforced mainly by the prompt — answer only
from context, otherwise say so.

**Model.** One model — gpt-oss-120b on Cerebras (free, fast) — answers both surfaces, with Llama 3.3 70B
on Groq / OpenRouter as automatic failover, so the service stays responsive even when one provider is busy.

**Grounding & safety.** The persona answers only from retrieved context, never reads out its sources,
and ignores prompt-injection attempts to change its role or reveal its instructions. PII (phone, email)
and internal Adda247 details (hostnames, infra identifiers) are redacted at ingest by `scripts/scrub.py`.

**Source documents.** The resume and interview notes are personal/PII, so the raw files are **not
committed**. The prebuilt vector store in `data/` (scrubbed, no PII) ships with the repo so the deploy
needs no source files; `scripts/ingest.py` rebuilds it from the originals when they are present locally.

## Layout

```
app/      main.py (API) · rag.py (retrieval) · persona.py (prompt) · llm.py (providers + failover) · tools.py (Cal.com) · static/
scripts/  scrub.py · summarize_repos.py · ingest.py · sources.py
evals/    golden_qa.yaml · run_chat_evals.py
livekit/  agent.py (LiveKit voice agent on the same backend)
```

## Run locally

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # then fill in keys

python scripts\scrub.py         # writes scrub_report.txt (review the redactions)
python scripts\summarize_repos.py
python scripts\ingest.py        # builds data/ — takes ~1-2 min

uvicorn app.main:app --reload   # open http://localhost:8000
```

The ingest steps need the source documents present locally. Cerebras and Groq keys are free (no card);
Cal.com is free; embeddings and the vector store run locally. If you only have the committed `data/`
store (no source files), skip the scrub/ingest steps and just run uvicorn.

## Deploy (Render, free)

1. Push this repo to GitHub (the prebuilt `data/` store is committed; source documents are not).
2. New → Web Service → connect the repo. Render reads `render.yaml`.
3. Add the env vars from `.env.example` in the Render dashboard.
4. Render installs deps and runs the app against the committed vector store — no source files needed.
5. Add a free https://cron-job.org job hitting `<render-url>/health` every 10 minutes so the free
   instance never sleeps and voice stays under 2s.

## Voice (Vapi, free signup credit)

1. Create an assistant at https://vapi.ai.
2. Model → Custom LLM → URL `https://<render-url>/v1/chat/completions`.
3. Transcriber: Deepgram. Voice: any low-latency voice. Enable interruptions / barge-in.
4. Provision a free phone number and attach the assistant.

Booking works over the phone with no extra Vapi config — the backend calls Cal.com itself and reads
back the confirmation.

## LiveKit browser agent (same brain, no phone)

`livekit/` holds a LiveKit Agents worker that drives the **same** backend as an OpenAI-compatible LLM —
so grounding, guardrails and Cal.com booking are identical; only the voice pipeline differs (Deepgram
STT/TTS, bundled Silero turn detection, WebRTC). It runs in the browser, needs no phone number, and stays
$0 on free tiers.

Free accounts: **LiveKit Cloud** (cloud.livekit.io) for `LIVEKIT_URL` / `LIVEKIT_API_KEY` /
`LIVEKIT_API_SECRET`, and **Deepgram** (console.deepgram.com) for `DEEPGRAM_API_KEY`.

```
cd livekit
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # fill LIVEKIT_* and DEEPGRAM_API_KEY

python agent.py console         # talk in the terminal (quick local test)
python agent.py dev             # run the worker for the browser demo
```

With the worker running (`dev`), open the **LiveKit Agents Playground**
(agents-playground.livekit.io), connect it to your LiveKit Cloud project, and talk in the browser.

## Evals

```
python evals\run_chat_evals.py   # retrieval precision/hit-rate + deterministic golden-set groundedness
```

Groundedness is scored deterministically against a manually-labelled golden set — key-fact coverage on
answerable questions plus refusal on adversarial prompts — so the results are exact and reproducible.

## Cost (per call / per chat session)

| Item | Cost | Notes |
|---|---|---|
| **Per chat session** | **$0** | local bge-small embeddings + free LLM (Cerebras gpt-oss-120b) + free Render host — no metered API on the path |
| **Per voice call** | **~$0.07–0.15 / min** (≈ $0.21–0.45 for a 3-min call) | drawn from Vapi's $10 free signup credit, so **$0 out of pocket** (~140 free minutes). Split: Vapi ~$0.05 + Deepgram STT ~$0.01 + TTS ~$0.01 / min; **LLM inference $0** (self-hosted) |
| **Monthly fixed** | **$0** | Render free tier + Cal.com free + cron-job.org free |

The one cost driver — the LLM — is self-hosted on free inference, so the largest per-call expense is zeroed
out and the phone is the only line item, fully covered by free trial credit.
