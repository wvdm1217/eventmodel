import asyncio
import pytest
from eventmodel import App, EventModel, StopEvent

# ==========================================
# 1. Define the Events
# ==========================================
class ProcessBatch(EventModel, topic="test_batch.process"):
    batch_id: str
    items: list[str]

class ProcessItem(EventModel, topic="test_item.process"):
    batch_id: str
    item_id: str

class ItemCompleted(EventModel, topic="test_item.completed"):
    batch_id: str
    item_id: str
    result: str

class BatchCompleted(EventModel, topic="test_batch.completed"):
    batch_id: str
    results: list[str]

# ==========================================
# 2. State Store (For Fan-In Aggregation)
# ==========================================
class BatchState:
    def __init__(self, total_items: int):
        self.total_items = total_items
        self.results: list[str] = []

@pytest.mark.asyncio
async def test_batch_fan_out_fan_in(capsys):
    app = App()
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
        await asyncio.sleep(0.1) # Small sleep to ensure parallel execution
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

    # Start the batch process
    await app.publish(ProcessBatch(batch_id="test_batch_01", items=["Item1", "Item2"]))
    
    # Run the app until StopEvent is emitted by the fan_in/completion service
    await app.run()
    
    # Verify the memory was cleaned up after successful aggregation
    assert len(active_batches) == 0
    
    # Verify the standard output matches expected workflow
    captured = capsys.readouterr()
    
    assert "[Fan-Out] Batch test_batch_01: Splitting 2 items..." in captured.out
    assert "[Worker] Processing Item1..." in captured.out
    assert "[Worker] Processing Item2..." in captured.out
    assert "[Fan-In] Accumulated result for" in captured.out
    assert "[Fan-In] Batch test_batch_01 is complete!" in captured.out
    assert "Final aggregated results:" in captured.out
    assert "'Item1_DONE'" in captured.out
    assert "'Item2_DONE'" in captured.out

