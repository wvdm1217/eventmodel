# EventModel

[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)
[![Tests](https://github.com/wvdm1217/eventmodel/actions/workflows/test.yml/badge.svg)](https://github.com/wvdm1217/eventmodel/actions/workflows/test.yml)
[![Pytest](https://img.shields.io/badge/tested_with-pytest-blue.svg)](https://docs.pytest.org/)

Build type-safe, event-driven Python apps with zero boilerplate. Inspired by FastAPI and SQLModel, EventModel turns Pydantic classes into self-routing events. Just type-hint your inputs to subscribe and use return statements to emit. Pure, clean, and heavily typed.

## Installation

```bash
uv add eventmodel
```

## Quick Start

Define your events, type-hint your handlers, and let the framework handle the routing.

```python
from eventmodel import App, EventModel

app = App()
users_app = App()

# 1. Define events with embedded routing metadata
class UserCreated(EventModel, topic="user.events.created"):
    user_id: int
    email: str

class SendWelcomeEmail(EventModel, topic="email.queue.outbound"):
    target_email: str
    body: str

# 2. Write pure domain logic. 
# The input type dictates the subscription topic.
# The return type dictates the emission topic.
@users_app.service()
async def process_new_user(event: UserCreated) -> SendWelcomeEmail:
    print(f"Processing new user: {event.user_id}")
    return SendWelcomeEmail(
        target_email=event.email, 
        body="Welcome!"
    )

app.include(users_app)
```

## Core Concepts

1. **Self-Routing Events:** By subclassing `EventModel` and specifying a `topic`, your data model intrinsically knows where it belongs on the message broker.
2. **Implicit Subscriptions:** Handlers use the `@service.service()` decorator. The framework reads the type-hint of the input argument to determine which topic to subscribe to.
3. **Implicit Emissions:** Handlers return initialized event objects. The framework automatically intercepts these returns and publishes them to their respective topics.
4. **Clean Architecture:** Domain functions remain entirely pure. They take an `EventModel` as input and return an `EventModel` as output—no broker logic mixed in.
5. **Modular Routing:** The framework supports `Service` instances that can be merged into a master `App` via `app.include()`.

