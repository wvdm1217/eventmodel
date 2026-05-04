"""
Tests for OpenTelemetry tracing integration.

These tests run with the opentelemetry-api + opentelemetry-sdk packages
installed.  The SDK is used *only* for in-test span capture; production
code only depends on the API.
"""

import pytest

pytest.importorskip("opentelemetry", reason="opentelemetry-api not installed")

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from eventmodel.models import EventModel
from eventmodel.service import Service
from eventmodel.tracing import (
    _OTEL_AVAILABLE,
    extract_trace_context,
    inject_trace_context,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────
# OTel's global TracerProvider can only be set once per process.
# We configure it once per module and clear the exporter between tests.


@pytest.fixture(scope="module")
def _otel_provider():
    """Configure a single in-memory TracerProvider for this test module."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    return exporter


@pytest.fixture(autouse=True)
def span_exporter(_otel_provider):
    """Clear recorded spans before and after each test."""
    _otel_provider.clear()
    yield _otel_provider
    _otel_provider.clear()


# ── Shared event definitions ──────────────────────────────────────────────────


class PingEvent(EventModel, topic="test.ping"):
    value: int


class PongEvent(EventModel, topic="test.pong"):
    result: str


# ── Unit tests for inject/extract helpers ─────────────────────────────────────


def test_otel_available():
    assert _OTEL_AVAILABLE is True


def test_inject_no_active_span():
    """inject_trace_context should be a no-op when there is no active span."""
    data = {"key": "value"}
    result = inject_trace_context(data)
    assert result == data
    assert result is data  # same object – nothing was added


def test_inject_active_span():
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("test-span"):
        data = {"key": "value"}
        result = inject_trace_context(data)

    assert result is not data  # new dict was created
    assert "key" in result
    # W3C traceparent must be present
    assert "_otel_traceparent" in result
    assert result["_otel_traceparent"].startswith("00-")


def test_extract_strips_otel_keys():
    tracer = trace.get_tracer("test")
    with tracer.start_as_current_span("producer"):
        enriched = inject_trace_context({"user_id": 42})

    clean, ctx = extract_trace_context(enriched)

    # Pydantic-safe: no OTel keys remain
    assert "_otel_traceparent" not in clean
    assert clean == {"user_id": 42}

    # Context is reconstructed
    assert ctx is not None


def test_extract_no_otel_keys():
    data = {"user_id": 1}
    clean, ctx = extract_trace_context(data)
    assert clean == data
    assert ctx is None


def test_roundtrip_preserves_trace_id():
    """The trace ID extracted from an injected payload must match the producer's."""
    tracer = trace.get_tracer("test")
    producer_trace_id = None

    with tracer.start_as_current_span("producer") as span:
        producer_trace_id = span.get_span_context().trace_id
        enriched = inject_trace_context({"x": 1})

    _, ctx = extract_trace_context(enriched)
    assert ctx is not None

    with tracer.start_as_current_span("consumer", context=ctx) as consumer_span:
        assert consumer_span.get_span_context().trace_id == producer_trace_id


# ── Integration tests: CONSUMER spans created by service wrapper ──────────────


@pytest.mark.asyncio
async def test_service_wrapper_creates_consumer_span(span_exporter):
    """The service wrapper must emit exactly one CONSUMER span per invocation."""
    service = Service()

    @service.service()
    async def handle_ping(event: PingEvent) -> None:  # type: ignore[return]
        pass

    wrapper = service.routes["test.ping"]
    await wrapper({"value": 7})

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "process test.ping"
    assert span.kind == trace.SpanKind.CONSUMER
    assert span.attributes["messaging.destination"] == "test.ping"
    assert span.attributes["eventmodel.handler"] == "handle_ping"


@pytest.mark.asyncio
async def test_service_wrapper_consumer_span_links_to_producer(span_exporter):
    """
    If a PRODUCER span embeds its context in the payload, the CONSUMER span
    created by the service wrapper must share the same trace.
    """
    tracer = trace.get_tracer("test")
    producer_trace_id = None

    with tracer.start_as_current_span("producer") as span:
        producer_trace_id = span.get_span_context().trace_id
        payload = inject_trace_context({"value": 99})

    service = Service()

    @service.service()
    async def handle_ping(event: PingEvent) -> None:  # type: ignore[return]
        pass

    wrapper = service.routes["test.ping"]
    await wrapper(payload)

    spans = span_exporter.get_finished_spans()
    consumer_span = next(s for s in spans if s.name == "process test.ping")
    assert consumer_span.get_span_context().trace_id == producer_trace_id


@pytest.mark.asyncio
async def test_service_wrapper_span_error_on_exception(span_exporter):
    """The CONSUMER span must be marked ERROR when the handler raises."""
    from opentelemetry.trace import StatusCode

    service = Service()

    @service.service()
    async def handle_ping(event: PingEvent) -> None:  # type: ignore[return]
        raise RuntimeError("boom")

    wrapper = service.routes["test.ping"]

    with pytest.raises(RuntimeError, match="boom"):
        await wrapper({"value": 1})

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].status.status_code == StatusCode.ERROR


# ── Integration tests: PRODUCER spans created by App._publish_async ───────────


@pytest.mark.asyncio
async def test_publish_creates_producer_span(span_exporter):
    """app.publish() must emit a PRODUCER span."""
    from unittest.mock import AsyncMock, MagicMock

    from eventmodel.app import App
    from eventmodel.broker import Broker

    mock_broker = MagicMock(spec=Broker)
    mock_broker.publish = AsyncMock()

    app = App(broker=mock_broker)
    await app.publish(PingEvent(value=5))

    spans = span_exporter.get_finished_spans()
    assert len(spans) == 1
    span = spans[0]
    assert span.name == "publish test.ping"
    assert span.kind == trace.SpanKind.PRODUCER
    assert span.attributes["messaging.destination"] == "test.ping"
    assert span.attributes["eventmodel.event_type"] == "PingEvent"


# ── Integration test: end-to-end trace propagation ────────────────────────────


@pytest.mark.asyncio
async def test_end_to_end_trace_propagation(span_exporter):
    """
    Full pipeline: App.publish → broker queue → service handler.
    All spans must share the same trace_id.
    """
    import asyncio

    from eventmodel.app import App
    from eventmodel.models import StopEvent

    class TriggerEvent(EventModel, topic="e2e.trigger"):
        pass

    class DoneEvent(EventModel, topic="e2e.done"):
        pass

    app = App()

    @app.service()
    async def on_trigger(event: TriggerEvent) -> DoneEvent:
        return DoneEvent()

    @app.service()
    async def on_done(event: DoneEvent) -> StopEvent:
        return StopEvent()

    await app.publish(TriggerEvent())
    await asyncio.wait_for(app.run(exit_on_idle=True), timeout=2.0)

    spans = span_exporter.get_finished_spans()
    # At minimum: publish trigger + process trigger + publish done + process done
    assert len(spans) >= 2

    trace_ids = {s.get_span_context().trace_id for s in spans}
    # All spans should belong to the same trace
    assert len(trace_ids) == 1
