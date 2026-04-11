from eventmodel import App
from events import UserCreated, SendWelcomeEmail

app = App()


@app.service()
async def process_new_user(event: UserCreated) -> SendWelcomeEmail:
    print(f"Processing domain logic for User: {event.user_id}")
    return SendWelcomeEmail(target_email=event.email, body="Welcome to the platform!")
