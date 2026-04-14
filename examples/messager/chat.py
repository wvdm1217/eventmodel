import asyncio
import sys

from models import JoinRequest, ListRequest, ListResponse, MessageDelivered, SendMessage

from eventmodel import App
from eventmodel.brokers.nats_broker import NatsBroker
from eventmodel.models import AlwaysEvent, StartEvent, StopEvent

broker = NatsBroker()
app = App(broker=broker)

current_username = ""


@app.service()
async def handle_list_response(event: ListResponse):
    """Filter and display the list response if it was requested by this client."""
    if event.requester == current_username:
        print(f"\n[Active Users]: {', '.join(event.users)}")
        print("> ", end="", flush=True)


@app.service()
async def handle_message_delivered(event: MessageDelivered):
    """Filter and display the message if it is intended for this client."""
    if event.recipient == current_username:
        print(f"\n[{event.sender}]: {event.text}")
        print("> ", end="", flush=True)


@app.service()
async def start_client(start_event: StartEvent) -> tuple[JoinRequest, AlwaysEvent]:
    """Initial event to kick off the client service."""
    welcome_message = (
        f"Welcome {current_username}! Commands: /list, /msg <user> <message>, /quit"
    )
    print(welcome_message)
    return JoinRequest(username=current_username), AlwaysEvent()


@app.service()
async def user_loop(event: AlwaysEvent) -> StopEvent | ListRequest | SendMessage | None:
    """Continuously read user input and emit corresponding events."""
    await asyncio.sleep(0.1)
    try:
        line = await asyncio.get_running_loop().run_in_executor(None, input, "> ")
    except EOFError:
        return StopEvent()

    line = line.strip()
    if not line:
        return None

    if line == "/quit":
        return StopEvent()
    elif line == "/list":
        return ListRequest(requester=current_username)
    elif line.startswith("/msg "):
        parts = line.split(" ", 2)
        if len(parts) < 3:
            print("Usage: /msg <user> <message>")
        else:
            _, recipient, text = parts
            return SendMessage(sender=current_username, recipient=recipient, text=text)
    else:
        print("Unknown command. Use /list, /msg <user> <message>, or /quit")
        return None


async def main():
    if len(sys.argv) < 2:
        print("Error: Username required for client mode.")
        print("Usage: uv run examples/messager/chat.py <username>")
        sys.exit(1)

    global current_username
    current_username = sys.argv[1]

    await app.run()


if __name__ == "__main__":
    # Suppress standard logging for a cleaner CLI interface
    import logging

    logging.getLogger("eventmodel").setLevel(logging.WARNING)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
