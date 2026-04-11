import asyncio
import uuid

from events import (
    InventoryReserved,
    NotificationRequested,
    OrderPlaced,
    OrderShipped,
    PaymentProcessed,
)

from eventmodel import App
from eventmodel.logger import logger

ecommerce_app = App()


@ecommerce_app.service()
async def process_payment(
    event: OrderPlaced,
) -> tuple[PaymentProcessed, NotificationRequested]:
    logger.info(
        f"[Payment Service] Processing payment of ${event.amount} for Order {event.order_id}"
    )
    await asyncio.sleep(0.5)

    return (
        PaymentProcessed(
            order_id=event.order_id, customer_id=event.customer_id, status="success"
        ),
        NotificationRequested(
            customer_id=event.customer_id,
            message=f"Payment of ${event.amount} successful for order {event.order_id}.",
        ),
    )


@ecommerce_app.service()
async def reserve_inventory(
    event: PaymentProcessed,
) -> InventoryReserved | NotificationRequested:
    if event.status != "success":
        logger.warning(
            f"[Inventory Service] Ignoring failed payment for Order {event.order_id}"
        )
        return NotificationRequested(
            customer_id=event.customer_id,
            message=f"Order {event.order_id} failed due to payment issues.",
        )

    logger.info(f"[Inventory Service] Reserving items for Order {event.order_id}")
    await asyncio.sleep(0.5)

    return InventoryReserved(order_id=event.order_id, customer_id=event.customer_id)


@ecommerce_app.service()
async def ship_order(
    event: InventoryReserved,
) -> tuple[OrderShipped, NotificationRequested]:
    tracking_num = f"TRK-{uuid.uuid4().hex[:8].upper()}"
    logger.info(
        f"[Shipping Service] Shipping Order {event.order_id}. Tracking: {tracking_num}"
    )
    await asyncio.sleep(0.5)

    return (
        OrderShipped(order_id=event.order_id, tracking_number=tracking_num),
        NotificationRequested(
            customer_id=event.customer_id,
            message=f"Order {event.order_id} has shipped! Tracking: {tracking_num}",
        ),
    )


@ecommerce_app.service()
async def send_notification(event: NotificationRequested) -> None:
    logger.info(
        f"[Notification Service] Sending message to Customer {event.customer_id}: '{event.message}'"
    )
    await asyncio.sleep(0.1)


@ecommerce_app.service()
async def close_order(event: OrderShipped) -> None:
    logger.info(f"[Order Completion] Order {event.order_id} has been fully processed.")
    await asyncio.sleep(0.1)
