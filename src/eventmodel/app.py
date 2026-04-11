import asyncio

from eventmodel.broker import AsyncioBroker, Broker
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
            print(f"[APP BOOT] Mounted listener for: '{topic}'")

    async def publish(self, event) -> None:
        """
        Manually publish an event to the broker.
        """
        target_topic = getattr(event, "__topic__", None)
        if not target_topic:
            raise ValueError(f"Event '{event.__class__.__name__}' is missing a topic.")
        await self.broker.publish(target_topic, event.to_message_payload())

    async def run(self) -> None:
        """
        Start the broker listener loop and all included services in the background.
        """
        print("[APP] Starting event listener loop and services...")
        tasks = [self.broker.listen(self.routes)]
        for service in self._included_services:
            tasks.append(service.run())
        
        await asyncio.gather(*tasks)
