from eventmodel.models import EventModel


class OrderPlaced(EventModel, topic="order.placed"):
    order_id: str
    customer_id: str
    amount: float


class PaymentProcessed(EventModel, topic="payment.processed"):
    order_id: str
    customer_id: str
    status: str


class InventoryReserved(EventModel, topic="inventory.reserved"):
    order_id: str
    customer_id: str


class OrderShipped(EventModel, topic="order.shipped"):
    order_id: str
    tracking_number: str


class NotificationRequested(EventModel, topic="notification.requested"):
    customer_id: str
    message: str
