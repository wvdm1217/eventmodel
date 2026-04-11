import asyncio
import json
from typing import Awaitable, Callable, Protocol


class Broker(Protocol):
    async def publish(self, topic: str, message: bytes) -> None:
        ...

    async def listen(self, routes: dict[str, Callable[[dict], Awaitable[list[tuple[str, bytes]] | None]]]) -> None:
        ...

    async def stop(self) -> None:
        ...


class AsyncioBroker:
    """
    Default in-memory message broker using asyncio.Queue.
    """
    def __init__(self):
        self.queue: asyncio.Queue[tuple[str, bytes]] = asyncio.Queue()
        self.tasks: list[asyncio.Task] = []

    async def publish(self, topic: str, message: bytes) -> None:
        await self.queue.put((topic, message))

    async def listen(self, routes: dict[str, Callable[[dict], Awaitable[list | None]]]) -> None:
        """
        Continuously consume events from the queue and route them.
        """
        async def worker():
            while True:
                try:
                    topic, message = await self.queue.get()
                    handler = routes.get(topic)
                    
                    if handler:
                        payload = json.loads(message.decode())
                        # Handler returns events to be published
                        emitted_events = await handler(payload)
                        if emitted_events:
                            for target_topic, event_bytes in emitted_events:
                                await self.publish(target_topic, event_bytes)
                    else:
                        print(f"[BROKER WARNING] No handler registered for topic: '{topic}'")
                        
                    self.queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    print(f"[BROKER ERROR] Error processing message: {e}")

        # Start a few workers
        for _ in range(3):
            task = asyncio.create_task(worker())
            self.tasks.append(task)
            
    async def stop(self):
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
