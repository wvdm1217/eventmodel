"""
Tests for optional OpenTelemetry tracing integration.

These tests run only when ``opentelemetry-sdk`` is installed (which it is in
the dev dependency group).  They verify that:

* Context is injected into / extracted from message payloads.
* Each service handler execution is wrapped in an OTel consumer span.
* The ``traceparent`` propagates through the full event chain so all spans
  share the same ``trace_id``.
"""

import json

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from eventmodel import tracing
from eventmodel.app import App
from eventmodel.brokers.asyncio_broker import AsyncioBroker
from eventmodel.models import EventModel
from eventmodel.service import Service


# ---------------------------------------------------------------------------
# Shared OTel provider — set once per test session to avoid the
# "Overriding of current TracerProvider is not allowed" warning.
# ---------------------------------------------------------------------------

_EXPORTER = InMemorySpanExporter()
_PROVIDER = TracerProvider()
_PROVIDER.add_span_processor(SimpleSpanProcessor(_EXPORTER))
trace.set_tracer_provider(_PROVIDER)


@pytest.fixture(autouse=True)
def clear_spans():
    """Reset the in-memory exporter before every test."""
    _EXPORTER.clear()
    yield


# ---------------------------------------------------------------------------
# Test event models
# ---------------------------------------------------------------------------


class SourceEvent(EventModel, topic="trace.source"):
    value: int


class SinkEvent(EventModel, topic="trace.sink"):
    value: int


# ---------------------------------------------------------------------------
# Unit tests for tracing helpers
# ---------------------------------------------------------------------------


def test_is_otel_available():
    assert tracing.is_otel_available() is True


def test_inject_context_adds_otel_key():
    tracer = trace.get_tracer("test")

    with tracer.start_as_current_span("root"):
        data: dict = {}
        tracing.inject_context(data)

    assert tracing._CARRIER_KEY in data
    assert "traceparent" in data[tracing._CARRIER_KEY]


def test_inject_context_noop_outside_span():
    """inject_context is harmless when there is no active span."""
    data: dict = {}
    tracing.inject_context(data)
    # No active span → propagator may inject an invalid traceparent or nothing;
    # either way the call must not raise.


def test_extract_context_removes_otel_key():
    tracer = trace.get_tracer("test")

    with tracer.start_as_current_span("root"):
        data: dict = {}
        tracing.inject_context(data)

    assert tracing._CARRIER_KEY in data
    ctx = tracing.extract_context(data)
    assert tracing._CARRIER_KEY not in data
    assert ctx is not None


def test_extract_context_returns_none_when_no_key():
    data: dict = {"foo": "bar"}
    ctx = tracing.extract_context(data)
    assert ctx is None
    # Original data unchanged
    assert data == {"foo": "bar"}


# ---------------------------------------------------------------------------
# Integration: spans are created for service handlers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_handler_creates_span():
    service = Service()

    @service.service()
    async def handle_source(event: SourceEvent) -> None:
        pass

    wrapper = service.routes["trace.source"]
    await wrapper({"value": 1})

    spans = _EXPORTER.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "handle_source"
    attrs = spans[0].attributes or {}
    assert attrs["messaging.destination"] == "trace.source"


@pytest.mark.asyncio
async def test_service_handler_emitted_events_carry_context():
    """Events emitted by a handler must contain an __otel__ carrier key."""
    service = Service()

    @service.service()
    async def handle_source(event: SourceEvent) -> SinkEvent:
        return SinkEvent(value=event.value)

    wrapper = service.routes["trace.source"]
    result = await wrapper({"value": 7})

    assert result is not None
    assert len(result) == 1
    _, payload, _ = result[0]

    data = json.loads(payload)
    assert tracing._CARRIER_KEY in data, "emitted event payload must carry OTel context"


@pytest.mark.asyncio
async def test_trace_propagates_across_handler_chain():
    """
    The trace_id must be the same across all spans in an event chain.

    Simulates: SourceEvent → handler_a (emits SinkEvent) → handler_b
    """
    service = Service()

    @service.service()
    async def handler_a(event: SourceEvent) -> SinkEvent:
        return SinkEvent(value=event.value)

    @service.service()
    async def handler_b(event: SinkEvent) -> None:
        pass

    wrapper_a = service.routes["trace.source"]
    wrapper_b = service.routes["trace.sink"]

    # Publish the root event (no parent trace)
    result_a = await wrapper_a({"value": 3})

    assert result_a is not None
    _, sink_payload, _ = result_a[0]

    sink_data = json.loads(sink_payload)

    # Feed the emitted event (with injected context) into handler_b
    await wrapper_b(sink_data)

    spans = _EXPORTER.get_finished_spans()
    assert len(spans) == 2

    trace_ids = {span.context.trace_id for span in spans}
    assert len(trace_ids) == 1, "all spans must belong to the same trace"

    span_names = {span.name for span in spans}
    assert span_names == {"handler_a", "handler_b"}


@pytest.mark.asyncio
async def test_app_publish_injects_context():
    """App.publish() must inject OTel context into the broker message."""
    captured: list[dict] = []

    class CapturingBroker(AsyncioBroker):
        async def publish(self, topic: str, message: bytes) -> None:
            captured.append(json.loads(message))

    app = App(broker=CapturingBroker())  # type: ignore[arg-type]

    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("root"):
        event = SourceEvent(value=42)
        await app.publish(event)

    assert len(captured) == 1
    assert tracing._CARRIER_KEY in captured[0]
