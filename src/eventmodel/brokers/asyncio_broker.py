import asyncio
import json
import logging

from eventmodel.broker import RouteMap

logger = logging.getLogger(__name__)


class AsyncioBroker:
    """
    Default in-memory message broker using asyncio.Queue.
    """

    def __init__(self):
        self.queue: asyncio.Queue[tuple[str, bytes]] = asyncio.Queue()
        self.tasks: list[asyncio.Task] = []

    async def publish(self, topic: str, message: bytes) -> None:
        await self.queue.put((topic, message))

    async def listen(self, routes: RouteMap, exit_on_idle: bool = False) -> None:
        """
        Continuously consume events from the queue and route them.
        """

        async def worker():
            while True:
                try:
                    topic, message = await self.queue.get()
                    try:
                        handler = routes.get(topic)

                        if handler:
                            try:
                                payload = json.loads(message.decode())
                            except json.JSONDecodeError:
                                logger.error(
                                    f"Malformed JSON payload for topic '{topic}'"
                                )
                            else:
                                # Handler returns events to be published
                                emitted_events = await handler(payload)
                                if emitted_events:
                                    for target_topic, event_bytes in emitted_events:
                                        await self.publish(target_topic, event_bytes)
                        else:
                            logger.warning(
                                f"No handler registered for topic: '{topic}'"
                            )
                    finally:
                        self.queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception:
                    logger.exception("Error processing message")

        # Start a few workers
        for _ in range(3):
            task = asyncio.create_task(worker())
            self.tasks.append(task)

        if exit_on_idle:
            await self.wait_until_idle()
            await self.stop()
        else:
            try:
                await asyncio.gather(*self.tasks)
            except asyncio.CancelledError:
                pass

    async def wait_until_idle(self) -> None:
        """
        Blocks until all items in the queue have been processed.
        """
        await self.queue.join()

    async def stop(self) -> None:
        """
        Cancel all worker tasks. Any messages remaining in the queue
        will be permanently lost as they are not persisted.
        """
        current_task = asyncio.current_task()
        other_tasks = [t for t in self.tasks if t is not current_task]

        for task in other_tasks:
            task.cancel()

        if other_tasks:
            await asyncio.gather(*other_tasks, return_exceptions=True)

        if current_task in self.tasks:
            current_task.cancel()
