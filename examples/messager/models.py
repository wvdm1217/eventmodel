from eventmodel import EventModel


class JoinRequest(EventModel, topic="chat.join"):
    username: str


class ListRequest(EventModel, topic="chat.list.request"):
    requester: str


class ListResponse(EventModel, topic="chat.list.response"):
    requester: str
    users: list[str]


class SendMessage(EventModel, topic="chat.message.send"):
    sender: str
    recipient: str
    text: str


class MessageDelivered(EventModel, topic="chat.message.delivered"):
    sender: str
    recipient: str
    text: str
