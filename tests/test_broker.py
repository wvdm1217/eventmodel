import asyncio
import json
import logging

import pytest

from eventmodel.broker import RouteMap
from eventmodel.brokers.asyncio_broker import AsyncioBroker

pytestmark = pytest.mark.asyncio


async def test_asyncio_broker_publish_and_listen():
    broker = AsyncioBroker()

    published_events: list[dict] = []

    async def handler(payload: dict) -> list[tuple[str, bytes]] | None:
        published_events.append(payload)
        return None

    routes: RouteMap = {"test.topic": handler}

    # Start workers
    listen_task = asyncio.create_task(broker.listen(routes))

    # Publish message
    await broker.publish("test.topic", json.dumps({"key": "value"}).encode())

    # Wait for the queue to be processed
    await broker.queue.join()

    assert len(published_events) == 1
    assert published_events[0] == {"key": "value"}

    # Cleanup
    await broker.stop()
    listen_task.cancel()


async def test_asyncio_broker_publish_emits_returned_events():
    broker = AsyncioBroker()

    published_events: list[dict] = []

    async def handler_a(payload: dict) -> list[tuple[str, bytes]] | None:
        return [("test.topic.b", json.dumps({"forwarded": True}).encode())]

    async def handler_b(payload: dict) -> list[tuple[str, bytes]] | None:
        published_events.append(payload)
        return None

    routes: RouteMap = {"test.topic.a": handler_a, "test.topic.b": handler_b}

    listen_task = asyncio.create_task(broker.listen(routes))
    await broker.publish("test.topic.a", json.dumps({"key": "value"}).encode())

    await broker.queue.join()

    assert len(published_events) == 1
    assert published_events[0] == {"forwarded": True}

    await broker.stop()
    listen_task.cancel()


async def test_asyncio_broker_handles_unregistered_topic(
    caplog: pytest.LogCaptureFixture,
):
    broker = AsyncioBroker()

    routes: RouteMap = {}
    listen_task = asyncio.create_task(broker.listen(routes))

    with caplog.at_level(logging.WARNING):
        await broker.publish("unknown.topic", b"{}")
        await broker.queue.join()

    assert "No handler registered for topic: 'unknown.topic'" in caplog.text

    await broker.stop()
    listen_task.cancel()


async def test_asyncio_broker_handles_malformed_json(caplog: pytest.LogCaptureFixture):
    broker = AsyncioBroker()

    async def dummy_handler(payload: dict) -> list[tuple[str, bytes]] | None:
        return None

    routes: RouteMap = {"test.topic": dummy_handler}
    listen_task = asyncio.create_task(broker.listen(routes))

    with caplog.at_level(logging.ERROR):
        await broker.publish("test.topic", b"not-json")
        await broker.queue.join()

    assert "Malformed JSON payload for topic 'test.topic'" in caplog.text

    await broker.stop()
    listen_task.cancel()
