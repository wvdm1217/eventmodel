import asyncio
from eventmodel import App, EventModel, StopEvent

app = App()

# ==========================================
# 1. Define the Events
# ==========================================
class ProcessBatch(EventModel, topic="batch.process"):
    batch_id: str
    items: list[str]

class ProcessItem(EventModel, topic="item.process"):
    batch_id: str
    item_id: str

class ItemCompleted(EventModel, topic="item.completed"):
    batch_id: str
    item_id: str
    result: str

class BatchCompleted(EventModel, topic="batch.completed"):
    batch_id: str
    results: list[str]

# ==========================================
# 2. State Store (For Fan-In Aggregation)
# ==========================================
class BatchState:
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.results: list[str] = []

active_batches: dict[str, BatchState] = {}

# ==========================================
# 3. Fan-Out Service
# ==========================================
@app.service()
async def fan_out(event: ProcessBatch) -> list[ProcessItem]:
    print(f"[Fan-Out] Batch {event.batch_id}: Splitting {len(event.items)} items...")
    active_batches[event.batch_id] = BatchState(total_items=len(event.items))
    return [
        ProcessItem(batch_id=event.batch_id, item_id=item) 
        for item in event.items
    ]

# ==========================================
# 4. Worker Service
# ==========================================
@app.service()
async def process_item(event: ProcessItem) -> ItemCompleted:
    print(f"  [Worker] Processing {event.item_id}...")
    await asyncio.sleep(0.5)
    return ItemCompleted(
        batch_id=event.batch_id, 
        item_id=event.item_id, 
        result=f"{event.item_id}_DONE"
    )

# ==========================================
# 5. Fan-In (Aggregation) Service
# ==========================================
@app.service()
async def fan_in(event: ItemCompleted) -> BatchCompleted | None:
    state = active_batches.get(event.batch_id)
    if not state:
        return None
        
    state.results.append(event.result)
    print(f"[Fan-In] Accumulated result for {event.item_id}. ({len(state.results)}/{state.total_items})")
    
    if len(state.results) == state.total_items:
        print(f"[Fan-In] Batch {event.batch_id} is complete!")
        results = state.results
        del active_batches[event.batch_id]
        return BatchCompleted(batch_id=event.batch_id, results=results)
        
    return None

# ==========================================
# 6. Completion Service
# ==========================================
@app.service()
async def on_batch_done(event: BatchCompleted) -> StopEvent:
    print(f"\n[Done] Final aggregated results: {event.results}")
    return StopEvent()

# ==========================================
# Main Execution
# ==========================================
async def main():
    print("Publishing initial batch request...")
    await app.publish(ProcessBatch(batch_id="batch_01", items=["TaskA", "TaskB", "TaskC"]))
    await app.run()

if __name__ == "__main__":
    asyncio.run(main())
