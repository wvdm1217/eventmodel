"""Minimal chat agent: the terminal and the LLM talk to each other only through events.

Run with: OPENAI_API_KEY=... uv run --with openai examples/chat-agent/main.py
"""

import asyncio
import logging

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from eventmodel import App, EventModel
from eventmodel.models import AlwaysEvent, StartEvent, StopEvent

app = App()
client = AsyncOpenAI()

history: list[ChatCompletionMessageParam] = [
    {"role": "system", "content": "You are a concise, friendly assistant."}
]


class UserMessage(EventModel, topic="user.message"):
    message: str


class AgentMessage(EventModel, topic="agent.message"):
    message: str


@app.service()
async def greet(event: StartEvent) -> AlwaysEvent:
    print("Chat started. Type a message, or /quit to exit.")
    return AlwaysEvent()


@app.service()
async def read_user_input(event: AlwaysEvent) -> UserMessage | StopEvent | None:
    """Re-runs forever (AlwaysEvent); each pass reads one line from the terminal."""
    try:
        line: str = (await asyncio.to_thread(input)).strip()
    except EOFError:
        return StopEvent()

    if line == "/quit":
        return StopEvent()
    if not line:
        return None
    return UserMessage(message=line)


@app.service()
async def handle_user_message(event: UserMessage) -> AgentMessage:
    history.append({"role": "user", "content": event.message})
    response = await client.chat.completions.create(
        model="gpt-6-luna", messages=history
    )
    reply = response.choices[0].message.content or ""
    history.append({"role": "assistant", "content": reply})
    return AgentMessage(message=reply)


@app.service()
async def show_agent_message(event: AgentMessage):
    print(f"{event.message}")


if __name__ == "__main__":
    logging.getLogger("eventmodel").setLevel(logging.WARNING)
    try:
        app.run()
    except KeyboardInterrupt:
        print("\nBye!")
