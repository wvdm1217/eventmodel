import asyncio
from typing import Set

from models import JoinRequest, ListRequest, ListResponse, MessageDelivered, SendMessage

from eventmodel import App
from eventmodel.brokers.nats_broker import NatsBroker

# We use NATS broker to allow multiple terminal processes to communicate.
# NATS server must be running (e.g., docker run -d -p 4222:4222 nats)
broker = NatsBroker(url="nats://localhost:4222")
app = App(broker=broker)

active_users: Set[str] = set()


@app.service()
async def handle_join(event: JoinRequest):
    """Register a new user."""
    active_users.add(event.username)
    print(f"[Server] User joined: {event.username}")


@app.service()
async def handle_list(event: ListRequest) -> ListResponse:
    """Respond with the list of active users."""
    print(f"[Server] List requested by: {event.requester}")
    return ListResponse(requester=event.requester, users=list(active_users))


@app.service()
async def handle_message(event: SendMessage) -> MessageDelivered:
    """Route a message to the recipient."""
    print(f"[Server] Routing message from {event.sender} to {event.recipient}")
    if event.recipient not in active_users:
        return MessageDelivered(
            sender="System",
            recipient=event.sender,
            text=f"User {event.recipient} is not online.",
        )
    return MessageDelivered(
        sender=event.sender, recipient=event.recipient, text=event.text
    )


async def main():
    print("Starting Chat Server...")

    await app.run()


if __name__ == "__main__":
    # Suppress standard logging for a cleaner CLI interface
    import logging

    logging.getLogger("eventmodel").setLevel(logging.WARNING)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
