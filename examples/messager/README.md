# EventModel CLI Messaging App

This example demonstrates how to build a multi-process, pub/sub application using `eventmodel` and NATS. It highlights how the framework handles routing naturally via Pydantic model return types, enabling a clean, decoupled architecture.

## Features
- **Server:** Maintains a simple in-memory state of connected users and routes messages.
- **Client:** Connects to the network, requests the active user list, and sends messages to specific users.

## Prerequisites

1.  **NATS Server:** Because clients and the server run in different processes, you must have a NATS server running. You can easily start one with Docker:
    ```bash
    docker run -d --rm -p 4222:4222 nats
    ```

2.  **Dependencies:** Ensure your `uv` environment includes the `nats` optional dependency group:
    ```bash
    uv sync --group nats
    ```

## Running the Example

Open up multiple terminal windows.

**Terminal 1 (Server):**
Start the central server to track users and route messages.
```bash
uv run examples/messager/server.py
```

**Terminal 2 (Client - Alice):**
Join the chat as "Alice".
```bash
uv run examples/messager/chat.py Alice
```

**Terminal 3 (Client - Bob):**
Join the chat as "Bob".
```bash
uv run examples/messager/chat.py Bob
```

## Usage

In any client window, you can type the following commands:
- `/list` - View all users currently registered with the server.
- `/msg <user> <message>` - Send a message to a specific user. (e.g., `/msg Alice Hello there!`)
- `/quit` - Exit the chat.
