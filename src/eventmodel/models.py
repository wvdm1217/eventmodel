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
        """Serializes the Pydantic model into a raw byte payload for brokers."""
        return self.model_dump_json().encode("utf-8")


class SystemEvent(EventModel):
    """
    Base class for all internal system events.
    These events are processed locally by the Python application
    and do not get published to the external message broker.
    """
    __topic__: ClassVar[Optional[str]] = None


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
