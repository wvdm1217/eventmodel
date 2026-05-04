# EventModel

[![PyPI version](https://badge.fury.io/py/python-eventmodel.svg)](https://badge.fury.io/py/python-eventmodel)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Pydantic v2](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/pydantic/pydantic/main/docs/badge/v2.json)](https://pydantic.dev)
[![Tests](https://github.com/wvdm1217/eventmodel/actions/workflows/test.yml/badge.svg)](https://github.com/wvdm1217/eventmodel/actions/workflows/test.yml)
[![Pytest](https://img.shields.io/badge/tested_with-pytest-blue.svg)](https://docs.pytest.org/)

**Documentation is available at [docs.eventmodel.app](https://docs.eventmodel.app/)**

Build type-safe, event-driven Python apps with zero boilerplate. Inspired by FastAPI and SQLModel, EventModel turns Pydantic classes into self-routing events. Just type-hint your inputs to subscribe and use return statements to emit. Pure, clean, and heavily typed.

## Installation

```bash
uv add python-eventmodel
```

## Quick Start

Define your events, type-hint your handlers, and let the framework handle the routing.

```python
from eventmodel import App, EventModel, StopEvent

app = App()

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
@app.service()
async def process_new_user(event: UserCreated) -> SendWelcomeEmail:
    print(f"Processing new user: {event.user_id}")
    return SendWelcomeEmail(
        target_email=event.email, 
        body="Welcome!"
    )

@app.service()
async def send_welcome_email(event: SendWelcomeEmail) -> StopEvent:
    print(f"Sending email to {event.target_email} with body: {event.body}")
    return StopEvent()


app.publish(UserCreated(user_id=123, email="user@example.com"))
app.run()
```

### Synchronous Handlers

EventModel is fully compatible with synchronous code. You can use standard `def` functions for your handlers instead of `async def`, and the framework will automatically execute them safely without blocking the main async event loop.

```python
@app.service()
def sync_process_new_user(event: UserCreated) -> SendWelcomeEmail:
    print(f"Sync processing user: {event.user_id}")
    return SendWelcomeEmail(
        target_email=event.email, 
        body="Welcome from sync!"
    )
```

## Core Concepts

1. **Self-Routing Events:** By subclassing `EventModel` and specifying a `topic`, your data model intrinsically knows where it belongs on the message broker.
2. **Implicit Subscriptions:** Handlers use the `@service.service()` decorator. The framework reads the type-hint of the input argument to determine which topic to subscribe to.
3. **Implicit Emissions:** Handlers return initialized event objects. The framework automatically intercepts these returns and publishes them to their respective topics.
4. **Clean Architecture:** Domain functions remain entirely pure. They take an `EventModel` as input and return an `EventModel` as output—no broker logic mixed in.
5. **Modular Routing:** The framework supports `Service` instances that can be merged into a master `App` via `app.include()`.

## OpenTelemetry Integration

EventModel has built-in, zero-configuration OpenTelemetry support. Install the optional extra to activate it:

```bash
uv add "python-eventmodel[otel]"
```

Once `opentelemetry-api` is present the framework automatically:

- Creates a **PRODUCER span** (`messaging.operation=publish`) every time an event is published via `app.publish()` or emitted from a handler.
- Creates a **CONSUMER span** (`messaging.operation=process`) every time a handler processes an event, annotated with the topic and handler name.
- **Propagates the W3C TraceContext** through the message payload so that all spans across an entire event chain share a single `trace_id` — even when events traverse an external broker like NATS.

No changes to your domain code are required.

### Wiring up an exporter

EventModel uses the standard OpenTelemetry global `TracerProvider`. Configure it once at startup with any exporter you like:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
trace.set_tracer_provider(provider)

# Now import and run your app — all spans flow to the exporter automatically.
from eventmodel import App, EventModel, StopEvent
...
```

A self-contained console-exporter example is available at [`examples/tracing.py`](examples/tracing.py).

### Attaching custom attributes

Use `eventmodel.get_tracer()` to obtain the same tracer the framework uses and add spans or attributes from within your handlers:

```python
from eventmodel import get_tracer

@app.service()
async def handle_order(event: OrderPlaced) -> InvoiceCreated:
    tracer = get_tracer()
    if tracer:
        with tracer.start_as_current_span("validate-stock"):
            # ... domain logic ...
            pass
    return InvoiceCreated(...)
```

### Span attributes reference

| Attribute | Value |
|---|---|
| `messaging.system` | `"eventmodel"` |
| `messaging.destination` | The event topic string |
| `messaging.operation` | `"publish"` or `"process"` |
| `eventmodel.handler` | Handler function name (CONSUMER spans only) |
| `eventmodel.event_type` | Event class name (PRODUCER spans only) |

