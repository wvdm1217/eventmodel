"""
OpenTelemetry integration for EventModel.

Provides a pre-configured tracer scoped to the ``eventmodel`` instrumentation
scope plus lightweight helpers for W3C TraceContext propagation through message
payloads.  When ``opentelemetry-api`` is *not* installed the module degrades
gracefully: all helpers become no-ops and no ``ImportError`` is raised.

Typical usage (SDK/exporter wired up by the application):

    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry import trace

    provider = TracerProvider()
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    # EventModel will automatically pick up the global provider.
"""

from __future__ import annotations

# ── Sentinel ─────────────────────────────────────────────────────────────────
# We deliberately avoid importing *anything* from opentelemetry at module-load
# time so that the library can be used without the optional dependency.
_OTEL_AVAILABLE: bool = False

try:
    from opentelemetry import context as otel_context
    from opentelemetry import propagate, trace
    from opentelemetry.trace import Tracer

    _OTEL_AVAILABLE = True
except ImportError:
    pass

# Prefix used to embed W3C TraceContext fields inside JSON payloads.
_TRACE_PREFIX = "_otel_"


# ── Public helpers ────────────────────────────────────────────────────────────


def get_tracer() -> "Tracer | None":  # type: ignore[name-defined]
    """
    Return the EventModel tracer backed by the globally configured provider.

    Returns ``None`` when the optional ``opentelemetry-api`` package is absent,
    letting callers guard cheaply: ``if tracer := get_tracer(): ...``.
    """
    if not _OTEL_AVAILABLE:
        return None
    return trace.get_tracer(
        "eventmodel",
        schema_url="https://opentelemetry.io/schemas/1.34.0",
    )


def inject_trace_context(data: dict) -> dict:
    """
    Inject the active W3C TraceContext fields into *data* and return the
    enriched copy.  The original dict is never mutated.

    When no span is active (or OTel is unavailable) the dict is returned
    unchanged, so callers do not need to guard against ``None``.
    """
    if not _OTEL_AVAILABLE:
        return data

    carrier: dict[str, str] = {}
    propagate.inject(carrier)
    if not carrier:
        return data

    enriched = dict(data)
    for key, value in carrier.items():
        enriched[f"{_TRACE_PREFIX}{key}"] = value
    return enriched


def extract_trace_context(
    data: dict,
) -> tuple[dict, "otel_context.Context | None"]:  # type: ignore[name-defined]
    """
    Strip ``_otel_*`` fields from *data*, reconstruct the W3C TraceContext
    they encode, and return ``(clean_data, ctx)``.

    *clean_data* never contains ``_otel_*`` keys, so it is safe to pass
    directly to a strict Pydantic model.  *ctx* is ``None`` when no trace
    fields were present or when OTel is unavailable.
    """
    if not _OTEL_AVAILABLE:
        return data, None

    carrier: dict[str, str] = {}
    clean: dict = {}

    for key, value in data.items():
        if key.startswith(_TRACE_PREFIX):
            carrier[key[len(_TRACE_PREFIX) :]] = value
        else:
            clean[key] = value

    ctx = propagate.extract(carrier) if carrier else None
    return clean, ctx
