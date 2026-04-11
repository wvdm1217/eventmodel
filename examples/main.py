import asyncio
from eventmodel import App
from services import app as users_app

# 1. Initialize Root App
app = App()

# 2. Mount domain services
app.include(users_app)

# --- Simulation for testing ---
async def simulate_incoming_message():
    print("\n--- Simulating Incoming Message ---")
    
    # 1. We receive raw JSON/Dict from Kafka/Redis on the "user.events.created" topic
    incoming_topic = "user.events.created"
    raw_payload = {"user_id": 42, "email": "test@example.com"}
    
    # 2. The framework looks up the wrapper and passes the raw payload
    handler_wrapper = app.routes.get(incoming_topic)
    if handler_wrapper:
        await handler_wrapper(raw_payload)

if __name__ == "__main__":
    asyncio.run(simulate_incoming_message())
