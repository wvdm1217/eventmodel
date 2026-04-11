from eventmodel.models import EventModel


class UserCreated(EventModel, topic="user.events.created"):
    user_id: int
    email: str


class SendWelcomeEmail(EventModel, topic="email.queue.outbound"):
    target_email: str
    body: str
