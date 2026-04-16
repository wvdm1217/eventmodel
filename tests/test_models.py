import pytest
from eventmodel.models import EventModel


def test_public_api_exports():
    """Ensure all user-facing event types are importable from the root package."""
    from eventmodel import AlwaysEvent, EventModel, StartEvent, StopEvent, SystemEvent  # noqa: F401


class UserCreated(EventModel, topic="user.events.created"):
    """Example event model for testing topic routing and payload serialization."""

    user_id: int
    username: str


def test_event_model_topic_binding() -> None:
    """Ensure topic metadata is bound properly through __init_subclass__."""
    assert UserCreated.__topic__ == "user.events.created"


def test_event_model_serialization() -> None:
    """Ensure standard JSON to byte payload serialization works for the broker."""
    event = UserCreated(user_id=1, username="alice")
    payload = event.to_message_payload()

    assert isinstance(payload, bytes)
    assert b'"user_id":1' in payload
    assert b'"username":"alice"' in payload


def test_event_model_strict_validation() -> None:
    """Ensure the strict=True config correctly rejects invalid data types."""
    with pytest.raises(ValueError):
        # We expect this to fail because we're passing a string to an int
        # and strict=True disables type coercion.
        UserCreated(user_id="not-an-int", username="alice")  # type: ignore
