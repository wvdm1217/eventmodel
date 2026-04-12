import asyncio
import json

from eventmodel import tracing
from eventmodel.broker import AsyncioBroker, Broker
from eventmodel.logger import logger
from eventmodel.service import Service


class App(Service):
    """
    The root application that orchestrates the message broker client
    and merges all sub-services together.
    """

    def __init__(self, broker: Broker | None = None):
        super().__init__()
        self.broker = broker or AsyncioBroker()
        self._included_services: list[Service] = []

    def include(self, service: Service) -> None:
        """
        Merges a sub-service's routes into the main application.
        Fails fast if two handlers try to listen to the same topic.
        """
        self._included_services.append(service)
        for topic, wrapper in service.routes.items():
            if topic in self.routes:
                raise ValueError(
                    f"Routing collision: A handler is already registered for topic '{topic}'"
                )
            self.routes[topic] = wrapper
            logger.info(f"Mounted listener for: '{topic}'")

    async def publish(self, event) -> None:
        """
        Manually publish an event to the broker.
        """
        target_topic = getattr(event, "__topic__", None)
        if not target_topic:
            raise ValueError(f"Event '{event.__class__.__name__}' is missing a topic.")
        # Inject the current OTel trace context so downstream service handlers
        # can attach their spans as children of the active trace.
        data = event.model_dump()
        tracing.inject_context(data)
        await self.broker.publish(
            target_topic, json.dumps(data, separators=(",", ":")).encode("utf-8")
        )

    async def run(self, exit_on_idle: bool = False) -> None:
        """
        Start the broker listener loop and all included services in the background.
        """
        logger.info("Starting event listener loop and services...")
        tasks = [self.broker.listen(self.routes, exit_on_idle=exit_on_idle)]
        for service in self._included_services:
            tasks.append(service.run())

        await asyncio.gather(*tasks)

    async def wait_until_idle(self) -> None:
        """
        Wait until the broker has processed all current messages.
        """
        if hasattr(self.broker, "wait_until_idle"):
            await self.broker.wait_until_idle()
