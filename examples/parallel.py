import asyncio
import time

from eventmodel import App, EventModel, StopEvent

app = App()


class JobEvent(EventModel, topic="job.execute"):
    job_id: int
    duration: float


class JobCompleted(EventModel, topic="job.completed"):
    job_id: int


@app.service()
async def process_job(event: JobEvent) -> JobCompleted:
    print(
        f"[{time.strftime('%X')}] Starting job {event.job_id} (duration: {event.duration}s)"
    )
    await asyncio.sleep(event.duration)
    print(f"[{time.strftime('%X')}] Finished job {event.job_id}")
    return JobCompleted(job_id=event.job_id)


TOTAL_JOBS = 10
completed_count = 0


@app.service()
async def on_job_completed(event: JobCompleted) -> StopEvent | None:
    global completed_count
    completed_count += 1
    if completed_count == TOTAL_JOBS:
        print(f"[{time.strftime('%X')}] All {TOTAL_JOBS} jobs completed. Stopping app.")
        return StopEvent()
    return None


async def main():
    print(f"[{time.strftime('%X')}] Queueing {TOTAL_JOBS} jobs...")
    for i in range(1, TOTAL_JOBS + 1):
        # Using 0.5s to clearly see the 5 workers running in parallel
        await app.publish(JobEvent(job_id=i, duration=1.0))

    print(f"[{time.strftime('%X')}] Starting App...")
    print(
        f"[{time.strftime('%X')}] Note: Default AsyncioBroker uses 5 concurrent workers."
    )
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
