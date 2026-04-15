from unittest.mock import AsyncMock, MagicMock

import pytest

from eventmodel.app import App
from eventmodel.broker import Broker
from eventmodel.models import EventModel
from eventmodel.service import Service


class DummyEvent(EventModel, topic="dummy.app.topic"):
    value: int


def test_app_initialization():
    app = App()
    assert app.broker is not None
    assert app._included_services == []
    assert app.routes == {}


def test_app_include_service():
    app = App()
    service = Service()

    @service.service()
    async def handler(event: DummyEvent) -> None:
        pass

    app.include(service)

    assert len(app._included_services) == 1
    assert "dummy.app.topic" in app.routes
    assert app.routes["dummy.app.topic"] == service.routes["dummy.app.topic"]


def test_app_include_service_collision():
    app = App()

    service1 = Service()

    @service1.service()
    async def handler1(event: DummyEvent) -> None:
        pass

    service2 = Service()

    @service2.service()
    async def handler2(event: DummyEvent) -> None:
        pass

    app.include(service1)

    with pytest.raises(ValueError, match="Routing collision"):
        app.include(service2)


@pytest.mark.asyncio
async def test_app_publish_event():
    mock_broker = MagicMock(spec=Broker)
    mock_broker.publish = AsyncMock()

    app = App(broker=mock_broker)

    event = DummyEvent(value=123)
    await app.publish(event)

    mock_broker.publish.assert_called_once()
    args = mock_broker.publish.call_args[0]
    assert args[0] == "dummy.app.topic"
    assert b'"value":123' in args[1]


def test_app_publish_event_sync():
    mock_broker = MagicMock(spec=Broker)
    mock_broker.publish = AsyncMock()

    app = App(broker=mock_broker)

    event = DummyEvent(value=123)
    app.publish(event)  # called synchronously without await

    mock_broker.publish.assert_called_once()
    args = mock_broker.publish.call_args[0]
    assert args[0] == "dummy.app.topic"
    assert b'"value":123' in args[1]


@pytest.mark.asyncio
async def test_app_publish_event_missing_topic():
    app = App()

    class BadEvent:
        pass

    with pytest.raises(ValueError, match="is missing a topic"):
        await app.publish(BadEvent())


@pytest.mark.asyncio
async def test_app_run():
    mock_broker = MagicMock(spec=Broker)
    mock_broker.listen = AsyncMock()

    app = App(broker=mock_broker)

    class MockService(Service):
        run_called: bool = False

        async def run(self) -> None:
            self.run_called = True

    service = MockService()

    @service.service()
    async def handler(event: DummyEvent) -> None:
        pass

    app.include(service)

    # We shouldn't actually block forever in the test if run() behaves correctly
    # However, app.run() awaits gather on tasks. The broker.listen() here is a mock,
    # so it will return immediately. service.run() is also a mock.
    await app.run()

    mock_broker.listen.assert_called_once()
    args, kwargs = mock_broker.listen.call_args
    assert "dummy.app.topic" in args[0]
    assert kwargs["exit_on_idle"] is False
    assert service.run_called


def test_app_run_sync():
    mock_broker = MagicMock(spec=Broker)
    mock_broker.listen = AsyncMock()

    app = App(broker=mock_broker)

    class MockService(Service):
        run_called: bool = False

        async def run(self) -> None:
            self.run_called = True

    service = MockService()

    @service.service()
    async def handler(event: DummyEvent) -> None:
        pass

    app.include(service)

    # test sync run
    app.run()

    mock_broker.listen.assert_called_once()
    args, kwargs = mock_broker.listen.call_args
    assert "dummy.app.topic" in args[0]
    assert kwargs["exit_on_idle"] is False
    assert service.run_called


@pytest.mark.asyncio
async def test_app_run_exit_on_idle():
    mock_broker = MagicMock(spec=Broker)
    mock_broker.listen = AsyncMock()

    app = App(broker=mock_broker)

    await app.run(exit_on_idle=True)

    mock_broker.listen.assert_called_once()
    args, kwargs = mock_broker.listen.call_args
    assert kwargs["exit_on_idle"] is True


@pytest.mark.asyncio
async def test_app_stops_on_service_return_stopevent():
    import asyncio
    from eventmodel.models import StopEvent

    app = App()

    class TriggerStopEvent(EventModel, topic="trigger.stop"):
        pass

    @app.service()
    async def handler(event: TriggerStopEvent) -> StopEvent:
        return StopEvent()

    await app.publish(TriggerStopEvent())

    # Should not block forever. If it does, the test will timeout and fail.
    await asyncio.wait_for(app.run(), timeout=0.5)


@pytest.mark.asyncio
async def test_app_stops_on_loop_yield_stopevent():
    import asyncio
    from eventmodel.models import StopEvent

    app = App()

    @app.loop()
    async def loop_func():
        yield StopEvent()

    # Should not block forever. If it does, the test will timeout and fail.
    try:
        await asyncio.wait_for(app.run(), timeout=0.5)
    except TimeoutError:
        print("Timeout in loop yield!")
        raise
