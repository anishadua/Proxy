# LiveKit voice agent

A LiveKit-native voice agent for the same persona. It reuses the deployed backend as an
OpenAI-compatible LLM, so the grounding, guardrails and Cal.com booking are identical to the
phone (Vapi) agent — only the voice pipeline differs.

```
browser / mic ──WebRTC──► LiveKit room ──► agent.py (livekit-agents)
                                            • Deepgram STT
                                            • LLM = https://proxy-ok1d.onrender.com/v1  (RAG + booking)
                                            • Deepgram TTS
                                            • Silero VAD (turn-taking, barge-in)
```

## Accounts (all free, no card)

- **LiveKit Cloud** — https://cloud.livekit.io → create a project → copy the **URL**, **API Key**, **API Secret**.
- **Deepgram** — https://console.deepgram.com → API key (free credit covers STT + TTS).

## Run

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          # fill LIVEKIT_* and DEEPGRAM_API_KEY
```

**Quick local test (terminal mic, no browser):**
```
python agent.py console
```

**Browser demo:**
```
python agent.py dev
```
Then open the **Agents Playground** at https://agents-playground.livekit.io, connect it to your
LiveKit Cloud project, and start talking. Share that page to demo the agent in a browser.

## Cost

$0 for a demo: LiveKit Cloud free tier + Deepgram free credit + the LLM on free inference. A phone
number would add SIP/telephony charges, so this build stays browser-only.
