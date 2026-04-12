"""
Optional OpenTelemetry tracing for eventmodel services.

Activated automatically when ``opentelemetry-api`` is installed
(``pip install eventmodel[otel]``).  When the package is absent every
helper is a transparent no-op so the rest of the framework stays clean.

Usage example (in your app entry-point)::

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))

    from opentelemetry import trace
    trace.set_tracer_provider(provider)

Eventmodel will then automatically create consumer spans for each service
handler and propagate the W3C ``traceparent`` / ``tracestate`` headers
through every message so the full event chain appears as one trace tree.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Generator

_OTEL_AVAILABLE = False

try:
    from opentelemetry import propagate, trace
    from opentelemetry.trace import SpanKind

    _OTEL_AVAILABLE = True
except ImportError:
    pass

# Reserved key used to carry W3C trace-context through the message payload.
# The service wrapper pops this field before constructing the EventModel so
# user-defined models never see it.
_CARRIER_KEY = "__otel__"


def is_otel_available() -> bool:
    """Return ``True`` when ``opentelemetry-api`` is installed."""
    return _OTEL_AVAILABLE


def inject_context(data: dict[str, Any]) -> None:
    """
    Inject the current OTel trace context into *data* in-place.

    Adds a ``__otel__`` key carrying the W3C ``traceparent`` (and optionally
    ``tracestate``) header so downstream consumers can attach their spans as
    children of the current trace.  A no-op when OTel is not installed.
    """
    if not _OTEL_AVAILABLE:
        return
    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    if carrier:
        data[_CARRIER_KEY] = carrier


def extract_context(data: dict[str, Any]) -> Any:
    """
    Pop the ``__otel__`` carrier from *data* and return the restored Context.

    The key is removed so the remaining dict is a clean event payload that
    can be handed to Pydantic without surprises.  Returns ``None`` when OTel
    is not installed or no context header was present.
    """
    if not _OTEL_AVAILABLE:
        return None
    carrier = data.pop(_CARRIER_KEY, None)
    if not carrier:
        return None
    return propagate.extract(carrier)


@contextmanager
def trace_handler(
    topic: str,
    handler_name: str,
    context: Any = None,
) -> Generator[Any, None, None]:
    """
    Context manager that wraps a service handler invocation in an OTel span.

    The span is tagged with standard OpenTelemetry messaging semantic
    conventions so it integrates cleanly with any OTel-aware observability
    back-end.  Yields ``None`` and does nothing when OTel is not installed.

    :param topic: The event topic being consumed (messaging.destination).
    :param handler_name: Name of the handler function (used as span name).
    :param context: Parent OTel ``Context`` extracted from the message, or
        ``None`` to start a new root trace.
    """
    if not _OTEL_AVAILABLE:
        yield None
        return

    tracer = trace.get_tracer("eventmodel")
    with tracer.start_as_current_span(
        handler_name,
        context=context,
        kind=SpanKind.CONSUMER,
        attributes={
            "messaging.system": "eventmodel",
            "messaging.destination": topic,
            "messaging.operation.name": "process",
        },
    ) as span:
        yield span
