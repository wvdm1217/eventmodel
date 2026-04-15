import asyncio
import json
import logging
from typing import Optional

import nats
from nats.aio.client import Client
from nats.aio.subscription import Subscription
from nats.errors import ConnectionClosedError

from eventmodel.broker import RouteMap
from eventmodel.config import settings

logger = logging.getLogger(__name__)


class NatsBroker:
    """
    NATS message broker implementation.
    """

    def __init__(self, url: str | None = None):
        self.url = url or settings.nats_url
        self.nc: Optional[Client] = None
        self.subscriptions: list[Subscription] = []
        self._is_listening = False
        self._stop_event = asyncio.Event()

    async def connect(self):
        if not self.nc:
            self.nc = await nats.connect(self.url)
            logger.info(f"Connected to NATS at {self.url}")

    async def publish(self, topic: str, message: bytes) -> None:
        if not self.nc:
            await self.connect()
        if self.nc:
            await self.nc.publish(topic, message)

    async def listen(self, routes: RouteMap, exit_on_idle: bool = False) -> None:
        if not self.nc:
            await self.connect()

        self._is_listening = True
        self._stop_event.clear()

        async def message_handler(msg):
            topic = msg.subject
            message = msg.data
            try:
                handler = routes.get(topic)
                if handler:
                    try:
                        payload = json.loads(message.decode())
                    except json.JSONDecodeError:
                        logger.error(f"Malformed JSON payload for topic '{topic}'")
                    else:
                        emitted_events = await handler(payload)
                        if emitted_events:
                            for target_topic, event_bytes in emitted_events:
                                await self.publish(target_topic, event_bytes)
                else:
                    logger.warning(f"No handler registered for topic: '{topic}'")
            except Exception:
                logger.exception(f"Error processing message from topic '{topic}'")

        if self.nc:
            for topic in routes.keys():
                sub = await self.nc.subscribe(topic, cb=message_handler)
                self.subscriptions.append(sub)
                logger.info(f"Subscribed to NATS topic: '{topic}'")

        if exit_on_idle:
            logger.warning(
                "NATS broker does not support exit_on_idle natively like queues do."
            )

        # Block until stopped
        await self._stop_event.wait()

    async def wait_until_idle(self) -> None:
        """
        NATS is pub/sub and doesn't hold messages in a queue like AsyncioBroker.
        This is a no-op for NATS.
        """
        pass

    async def stop(self) -> None:
        self._stop_event.set()
        for sub in self.subscriptions:
            try:
                await sub.unsubscribe()
            except ConnectionClosedError:
                pass
        self.subscriptions = []

        if self.nc and not self.nc.is_closed:
            await self.nc.close()
            logger.info("Disconnected from NATS")
