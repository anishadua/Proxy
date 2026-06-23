import os

from dotenv import load_dotenv
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import deepgram, openai

load_dotenv()

GREETING = (
    "Hi! I'm Anisha's AI representative. I can tell you about her background and projects, "
    "or help you book a quick call with her. What would you like to know?"
)

# The persona, grounding and booking all live in the shared backend, reached as an
# OpenAI-compatible LLM. The backend ignores instructions sent from here.
PROXY_LLM_URL = os.getenv("PROXY_LLM_URL", "https://proxy-ok1d.onrender.com/v1")


class Persona(Agent):
    def __init__(self):
        super().__init__(instructions="You are Anisha's AI representative.")


async def entrypoint(ctx: JobContext):
    await ctx.connect()
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=openai.LLM(model="proxy", base_url=PROXY_LLM_URL, api_key="proxy"),
        tts=deepgram.TTS(),
    )
    await session.start(agent=Persona(), room=ctx.room)
    await session.say(GREETING, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
