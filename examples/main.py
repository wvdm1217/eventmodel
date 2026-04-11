import asyncio
from eventmodel import App
from services import app as users_app
from events import UserCreated

# 1. Initialize Root App
app = App()

# 2. Mount domain services
app.include(users_app)

# --- Simulation for testing ---
async def simulate_incoming_message():
    print("\n--- Simulating Incoming Message ---")
    
    # 1. Start the application listener in the background
    listener_task = asyncio.create_task(app.run())
    
    # 2. We publish a new user event, which will be routed to the correct handler
    event = UserCreated(user_id=42, email="test@example.com")
    await app.publish(event)
    
    # 3. Give it a moment to process before shutting down
    await asyncio.sleep(0.1)
    
    # 4. Gracefully stop the listener
    await app.broker.stop()
    listener_task.cancel()

if __name__ == "__main__":
    asyncio.run(simulate_incoming_message())
