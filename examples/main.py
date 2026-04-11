from events import OrderPlaced
from services import ecommerce_app

from eventmodel import App
from eventmodel.logger import logger

app = App()
app.include(ecommerce_app)


async def main():
    logger.info("--- Starting E-Commerce Event-Driven Pipeline ---")

    event = OrderPlaced(order_id="ORD-9921", customer_id="CUST-ALPHA", amount=149.99)
    logger.info(f"[External] Publishing OrderPlaced event for {event.order_id}...")
    await app.publish(event)

    # Process all messages in the queue and exit when idle
    await app.run(exit_on_idle=True)

    logger.info("--- Shutting Down ---")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
