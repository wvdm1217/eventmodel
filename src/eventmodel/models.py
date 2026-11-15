from typing import ClassVar, Optional

from pydantic import BaseModel, ConfigDict


class EventModel(BaseModel):
    """
    Base class for all domain events.
    Uses __init_subclass__ to capture routing metadata exactly like SQLModel.
    """

    __topic__: ClassVar[Optional[str]] = None

    model_config = ConfigDict(strict=True)

    def __init_subclass__(cls, topic: str | None = None, **kwargs):
        # Pass remaining kwargs up to Pydantic's BaseModel
        super().__init_subclass__(**kwargs)

        # Bind the infrastructure topic to the class
        if topic:
            cls.__topic__ = topic

    def to_message_payload(self) -> bytes:
        """
        Serialize the model into a raw byte payload for brokers.

        If an active OpenTelemetry span exists the current W3C TraceContext is
        embedded as ``_otel_*`` fields so that consuming services can restore
        the trace lineage without requiring a separate headers channel.
        """
        from eventmodel.tracing import inject_trace_context

        data = inject_trace_context(self.model_dump())
        import json

        return json.dumps(data, separators=(",", ":")).encode("utf-8")


class SystemEvent(EventModel):
    """
    Base class for all internal system events.
    These events are processed locally by the Python application
    and do not get published to the external message broker.
    """


class StartEvent(SystemEvent, topic="__sys.start__"):
    """
    Fired automatically when the application starts.
    """

    pass


class AlwaysEvent(SystemEvent, topic="__sys.always__"):
    """
    A special system event that, when handled, automatically re-triggers itself
    after the handler completes, acting as a continuous background loop.
    """

    pass


class StopEvent(SystemEvent, topic="__sys.stop__"):
    """
    Yield or return this event to signal the application to stop.
    """

    pass
