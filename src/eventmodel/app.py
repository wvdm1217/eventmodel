import asyncio
import inspect
from typing import Callable

from eventmodel.broker import Broker
from eventmodel.logger import logger
from eventmodel.service import Service


class App(Service):
    """
    The root application that orchestrates the message broker client
    and merges all sub-services together.
    """

    def __init__(
        self, broker: Broker | str | None = None, worker_count: int | None = None
    ):
        super().__init__()
        from eventmodel.config import settings

        self.system_queue: asyncio.Queue = asyncio.Queue()
        self.worker_count = (
            worker_count if worker_count is not None else settings.worker_count
        )

        if broker == "NATS":
            from eventmodel.brokers.nats_broker import NatsBroker

            self.broker = NatsBroker()
        elif broker == "asyncio" or broker is None:
            from eventmodel.brokers.asyncio_broker import AsyncioBroker

            self.broker = AsyncioBroker(worker_count=self.worker_count)
        elif isinstance(broker, str):
            raise ValueError(f"Unknown broker type: {broker}")
        else:
            self.broker = broker

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

    async def _publish_async(self, event) -> None:
        """
        Manually publish an event to the broker asynchronously.
        """
        from eventmodel.models import SystemEvent

        target_topic = getattr(event, "__topic__", None)
        if not target_topic:
            raise ValueError(f"Event '{event.__class__.__name__}' is missing a topic.")

        if isinstance(event, SystemEvent):
            await self.system_queue.put(event)
        else:
            await self.broker.publish(target_topic, event.to_message_payload())

    def publish(self, event):
        """
        Manually publish an event to the broker.
        If an event loop is running, returns a coroutine.
        Otherwise, runs synchronously.
        """
        try:
            asyncio.get_running_loop()
            return self._publish_async(event)
        except RuntimeError:
            return asyncio.run(self._publish_async(event))

    async def _system_event_loop(self):
        from eventmodel.models import AlwaysEvent, StopEvent, SystemEvent

        while True:
            try:
                event_obj = await self.system_queue.get()
            except asyncio.CancelledError:
                break

            try:
                topic = getattr(event_obj, "__topic__", None)
                handler = None
                if isinstance(topic, str):
                    handler = self.routes.get(topic)

                has_stop = False
                if handler:
                    payload = event_obj.model_dump()
                    emitted_events = await handler(payload)

                    if emitted_events:
                        for (
                            target_topic,
                            payload_bytes,
                            out_event_obj,
                        ) in emitted_events:
                            if isinstance(out_event_obj, StopEvent):
                                await self.stop()
                                has_stop = True
                            elif isinstance(out_event_obj, SystemEvent):
                                await self.system_queue.put(out_event_obj)
                            else:
                                await self.publish(out_event_obj)

                if isinstance(event_obj, AlwaysEvent) and not has_stop:
                    await self.system_queue.put(AlwaysEvent())

            except Exception:
                logger.exception("Error processing system event")
            finally:
                self.system_queue.task_done()

    async def _run_loop(self, loop_func: Callable):
        from eventmodel.models import StopEvent

        try:
            if inspect.isasyncgenfunction(loop_func):
                async for event in loop_func():
                    if isinstance(event, StopEvent):
                        await self.stop()
                        break
                    await self.publish(event)
            else:
                await loop_func()
        except asyncio.CancelledError:
            pass

    async def _run_async(self, exit_on_idle: bool = False) -> None:
        """
        Start the broker listener loop and all included services in the background asynchronously.
        """
        logger.info("Starting event listener loop and services...")
        self._loop_tasks = []

        # Start system event loop
        self._loop_tasks.append(asyncio.create_task(self._system_event_loop()))

        # Fire StartEvent automatically
        from eventmodel.models import StartEvent

        await self.system_queue.put(StartEvent())

        for service in self._included_services + [self]:
            if hasattr(service, "loops"):
                for loop_func in service.loops:
                    self._loop_tasks.append(
                        asyncio.create_task(self._run_loop(loop_func))
                    )

            # Legacy background task hook
            if service is not self:
                self._loop_tasks.append(asyncio.create_task(service.run()))

        from eventmodel.models import StopEvent, SystemEvent

        def is_system_handler(handler: Callable) -> bool:
            try:
                params = list(inspect.signature(handler).parameters.values())
            except TypeError, ValueError:
                return False

            if not params:
                return False

            event_annotation = params[0].annotation
            if event_annotation is inspect.Signature.empty:
                return False

            try:
                return issubclass(event_annotation, SystemEvent)
            except TypeError:
                return False

        broker_routes = {}
        for topic, handler in self.routes.items():
            handler_is_system = is_system_handler(handler)
            if topic.startswith("__sys.") and not handler_is_system:
                raise ValueError(
                    f"Topic prefix '__sys.' is reserved for system event routes: {topic}"
                )

            if not handler_is_system:

                def make_wrapper(orig_handler):
                    async def broker_wrapper(payload):
                        emitted_events = await orig_handler(payload)
                        if not emitted_events:
                            return None
                        broker_emits = []
                        for target_topic, payload_bytes, event_obj in emitted_events:
                            if isinstance(event_obj, StopEvent):
                                await self.stop()
                            elif isinstance(event_obj, SystemEvent):
                                await self.system_queue.put(event_obj)
                            else:
                                broker_emits.append((target_topic, payload_bytes))
                        return broker_emits

                    return broker_wrapper

                broker_routes[topic] = make_wrapper(handler)

        broker_task = asyncio.create_task(
            self.broker.listen(broker_routes, exit_on_idle=exit_on_idle)
        )

        try:
            await broker_task
        finally:
            for task in self._loop_tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*self._loop_tasks, return_exceptions=True)

    def run(self, exit_on_idle: bool = False):
        """
        Start the broker listener loop and all included services in the background.
        If an event loop is running, returns a coroutine.
        Otherwise, runs synchronously.
        """
        try:
            asyncio.get_running_loop()
            return self._run_async(exit_on_idle=exit_on_idle)
        except RuntimeError:
            return asyncio.run(self._run_async(exit_on_idle=exit_on_idle))

    async def wait_until_idle(self) -> None:
        """
        Wait until the broker has processed all current messages.
        """
        if hasattr(self.broker, "wait_until_idle"):
            await self.broker.wait_until_idle()

    async def stop(self) -> None:
        """
        Stop the application and broker.
        """
        if hasattr(self.broker, "stop"):
            await self.broker.stop()
