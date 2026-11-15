"""
OpenTelemetry tracing example for EventModel.

This example demonstrates how to wire a TracerProvider with a
ConsoleSpanExporter so that every span is printed to stdout.

Requirements:
    uv add opentelemetry-api opentelemetry-sdk

Run:
    uv run examples/tracing.py
"""

import asyncio

# ── 1. Configure the SDK *before* importing the App ───────────────────────────
#    EventModel picks up whatever global TracerProvider has been set.
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

provider = TracerProvider()
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)

# ── 2. Normal EventModel usage ─────────────────────────────────────────────────
from eventmodel import App, EventModel, StopEvent  # noqa: E402

app = App()


class OrderPlaced(EventModel, topic="order.placed"):
    order_id: int
    amount: float


class InvoiceCreated(EventModel, topic="invoice.created"):
    order_id: int
    invoice_ref: str


class NotificationSent(EventModel, topic="notification.sent"):
    message: str


@app.service()
async def handle_order(event: OrderPlaced) -> InvoiceCreated:
    print(f"[handler] Processing order #{event.order_id} (${event.amount:.2f})")
    return InvoiceCreated(
        order_id=event.order_id,
        invoice_ref=f"INV-{event.order_id:05d}",
    )


@app.service()
async def handle_invoice(event: InvoiceCreated) -> NotificationSent:
    print(f"[handler] Invoice {event.invoice_ref} created for order #{event.order_id}")
    return NotificationSent(message=f"Invoice {event.invoice_ref} is ready.")


@app.service()
async def handle_notification(event: NotificationSent) -> StopEvent:
    print(f"[handler] Notification sent: {event.message}")
    return StopEvent()


async def main() -> None:
    # Publish the root event inside a manual span so the entire chain
    # inherits a single root trace-id – demonstrating context propagation.
    tracer = trace.get_tracer("example")
    with tracer.start_as_current_span("place-order"):
        await app.publish(OrderPlaced(order_id=42, amount=199.99))

    await app.run(exit_on_idle=True)

    # Flush pending spans before exit
    provider.force_flush()


if __name__ == "__main__":
    asyncio.run(main())
