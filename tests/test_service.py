import pytest

from eventmodel.models import EventModel
from eventmodel.service import Service


class DummyEvent(EventModel, topic="dummy.topic"):
    value: int


class AnotherEvent(EventModel, topic="another.topic"):
    name: str


def test_service_initialization():
    service = Service()
    assert service.routes == {}


def test_service_decorator_registers_route():
    service = Service()

    @service.service()
    async def handle_dummy(event: DummyEvent) -> None:
        pass

    assert "dummy.topic" in service.routes
    assert callable(service.routes["dummy.topic"])


@pytest.mark.asyncio
async def test_service_wrapper_execution():
    service = Service()

    handled_value = None

    @service.service()
    async def handle_dummy(event: DummyEvent) -> None:
        nonlocal handled_value
        handled_value = event.value

    # The routes map stores wrappers that take dict payload and return emitted events
    wrapper = service.routes["dummy.topic"]

    result = await wrapper({"value": 42})

    assert handled_value == 42
    assert result is None


@pytest.mark.asyncio
async def test_service_wrapper_execution_sync():
    service = Service()

    handled_value = None

    @service.service()
    def handle_dummy(event: DummyEvent) -> None:
        nonlocal handled_value
        handled_value = event.value

    wrapper = service.routes["dummy.topic"]

    result = await wrapper({"value": 42})

    assert handled_value == 42
    assert result is None


@pytest.mark.asyncio
async def test_service_wrapper_emits_single_event():
    service = Service()

    @service.service()
    async def handle_dummy(event: DummyEvent) -> AnotherEvent:
        return AnotherEvent(name=str(event.value))

    wrapper = service.routes["dummy.topic"]

    result = await wrapper({"value": 42})

    assert result is not None
    assert len(result) == 1
    topic, payload, obj = result[0]
    assert topic == "another.topic"
    assert b'"name":"42"' in payload
    assert isinstance(obj, AnotherEvent)


@pytest.mark.asyncio
async def test_service_wrapper_emits_multiple_events():
    service = Service()

    @service.service()
    async def handle_dummy(event: DummyEvent) -> list[AnotherEvent]:
        return [AnotherEvent(name="first"), AnotherEvent(name="second")]

    wrapper = service.routes["dummy.topic"]

    result = await wrapper({"value": 42})

    assert result is not None
    assert len(result) == 2
    assert result[0][0] == "another.topic"
    assert b'"name":"first"' in result[0][1]
    assert result[1][0] == "another.topic"
    assert b'"name":"second"' in result[1][1]


def test_service_decorator_requires_one_argument():
    service = Service()

    with pytest.raises(ValueError, match="must take exactly one argument"):

        @service.service()
        async def handle_dummy() -> None:
            pass


def test_service_decorator_requires_eventmodel_typehint():
    service = Service()

    with pytest.raises(
        TypeError, match="must be type-hinted with a subclass of EventModel"
    ):

        @service.service()
        async def handle_dummy(event: dict) -> None:
            pass


def test_service_decorator_requires_topic_on_eventmodel():
    class TopiclessEvent(EventModel):
        pass

    service = Service()

    with pytest.raises(ValueError, match="is missing a topic parameter"):

        @service.service()
        async def handle_dummy(event: TopiclessEvent) -> None:
            pass


@pytest.mark.asyncio
async def test_service_wrapper_validates_returned_type():
    service = Service()

    @service.service()
    async def handle_dummy(event: DummyEvent):
        return {"not": "an eventmodel"}

    wrapper = service.routes["dummy.topic"]

    with pytest.raises(TypeError, match="is not an EventModel"):
        await wrapper({"value": 42})


@pytest.mark.asyncio
async def test_service_wrapper_validates_returned_event_has_topic():
    class ReturnTopiclessEvent(EventModel):
        pass

    service = Service()

    @service.service()
    async def handle_dummy(event: DummyEvent):
        return ReturnTopiclessEvent()

    wrapper = service.routes["dummy.topic"]

    with pytest.raises(ValueError, match="is missing a topic"):
        await wrapper({"value": 42})
