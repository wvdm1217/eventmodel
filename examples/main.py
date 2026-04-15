from eventmodel import App, EventModel, StopEvent

app = App()

# 1. Define events with embedded routing metadata
class UserCreated(EventModel, topic="user.events.created"):
    user_id: int
    email: str

class SendWelcomeEmail(EventModel, topic="email.queue.outbound"):
    target_email: str
    body: str

# 2. Write pure domain logic. 
# The input type dictates the subscription topic.
# The return type dictates the emission topic.
@app.service()
async def process_new_user(event: UserCreated) -> SendWelcomeEmail:
    print(f"Processing new user: {event.user_id}")
    return SendWelcomeEmail(
        target_email=event.email, 
        body="Welcome!"
    )

@app.service()
async def send_welcome_email(event: SendWelcomeEmail) -> StopEvent:
    print(f"Sending email to {event.target_email} with body: {event.body}")
    return StopEvent()

async def main():
    await app.publish(UserCreated(user_id=123, email="user@example.com"))
    await app.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())