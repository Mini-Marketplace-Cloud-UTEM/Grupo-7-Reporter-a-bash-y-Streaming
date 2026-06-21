import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from google.cloud import pubsub_v1
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.schemas.events import (
    EventEnvelope,
    InventoryShortagePayload,
    OrderCreatedPayload,
    PaymentApprovedPayload,
    ShipmentDeliveredPayload,
)
from app.services.analytics_service import upsert_sales_from_order, upsert_top_product

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_order_created(payload: dict, correlation_id: str) -> None:
    data = OrderCreatedPayload(**payload)
    async with AsyncSessionLocal() as db:
        await upsert_sales_from_order(db, data.createdAt, Decimal(str(data.totalAmount)), correlation_id)
    logger.info("order_created orderId=%s correlationId=%s", data.orderId, correlation_id)


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_payment_approved(payload: dict, correlation_id: str) -> None:
    data = PaymentApprovedPayload(**payload)
    logger.info("payment_approved paymentId=%s orderId=%s correlationId=%s", data.paymentId, data.orderId, correlation_id)


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_inventory_shortage(payload: dict, correlation_id: str) -> None:
    data = InventoryShortagePayload(**payload)
    logger.warning(
        "inventory_shortage productId=%s currentStock=%d requested=%d correlationId=%s",
        data.productId, data.currentStock, data.requestedQuantity, correlation_id,
    )


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_shipment_delivered(payload: dict, correlation_id: str) -> None:
    data = ShipmentDeliveredPayload(**payload)
    logger.info(
        "shipment_delivered shipmentId=%s orderId=%s city=%s correlationId=%s",
        data.shipment_id, data.order_id, data.city, correlation_id,
    )


_HANDLERS = {
    "OrderCreated": _handle_order_created,
    "PaymentApproved": _handle_payment_approved,
    "InventoryShortage": _handle_inventory_shortage,
    "ShipmentDelivered": _handle_shipment_delivered,
}


def _make_callback(loop: asyncio.AbstractEventLoop):
    def callback(message: pubsub_v1.subscriber.message.Message) -> None:
        try:
            raw = json.loads(message.data.decode("utf-8"))
            envelope = EventEnvelope(**raw)
            handler = _HANDLERS.get(envelope.eventType)
            if handler:
                future = asyncio.run_coroutine_threadsafe(
                    handler(envelope.payload, str(envelope.correlationId)), loop
                )
                future.result(timeout=30)
                message.ack()
            else:
                logger.warning("unknown_event_type type=%s", envelope.eventType)
                message.ack()
        except Exception:
            logger.exception("pubsub_callback_error message_id=%s", message.message_id)
            message.nack()

    return callback


async def start_consumers() -> list:
    loop = asyncio.get_running_loop()
    subscriber = pubsub_v1.SubscriberClient()
    callback = _make_callback(loop)

    subscriptions = [
        settings.PUBSUB_SUBSCRIPTION_ORDER_CREATED,
        settings.PUBSUB_SUBSCRIPTION_PAYMENT_APPROVED,
        settings.PUBSUB_SUBSCRIPTION_INVENTORY_SHORTAGE,
        settings.PUBSUB_SUBSCRIPTION_SHIPMENT_DELIVERED,
    ]

    futures = []
    for sub in subscriptions:
        if not sub:
            continue
        future = subscriber.subscribe(sub, callback=callback)
        futures.append(future)
        logger.info("pubsub_subscribed subscription=%s", sub)

    return futures


async def stop_consumers(futures: list) -> None:
    for future in futures:
        future.cancel()
