"""
Worker de consumo de eventos desde Google Cloud Pub/Sub.

Se suscribe a los cuatro tópicos del ecosistema y despacha cada mensaje
al handler correspondiente según el campo eventType del envelope estándar.
Implementa reintentos con Exponential Backoff (máximo 5 intentos) usando tenacity.
"""

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
from app.services.analytics_service import (
    insert_inventory_shortage,
    insert_order_status,
    insert_shipment_delivery,
    upsert_sales_from_order,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_order_created(payload: dict, correlation_id: str) -> None:
    """Acumula las ventas del pedido en fact_sales_summary (modo REAL_TIME)."""
    data = OrderCreatedPayload(**payload)
    async with AsyncSessionLocal() as db:
        await upsert_sales_from_order(
            db, data.createdAt, Decimal(str(data.totalAmount)), correlation_id
        )
        # Si el pedido trae estado, lo anotamos en order_status_log para que
        # /reports/orders-by-status pueda contarlo (tarea 2.3 de Fran).
        if data.status:
            await insert_order_status(
                db, order_id=data.orderId, status=data.status, occurred_at=data.createdAt
            )
    logger.info("evento_order_created orderId=%s correlationId=%s", data.orderId, correlation_id)


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_payment_approved(payload: dict, correlation_id: str) -> None:
    """Registra la aprobación del pago. Por ahora solo se loguea para trazabilidad."""
    data = PaymentApprovedPayload(**payload)
    logger.info(
        "evento_payment_approved paymentId=%s orderId=%s correlationId=%s",
        data.paymentId,
        data.orderId,
        correlation_id,
    )


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_inventory_shortage(payload: dict, correlation_id: str) -> None:
    """Guarda la alerta de quiebre de stock en inventory_shortage_log."""
    data = InventoryShortagePayload(**payload)
    async with AsyncSessionLocal() as db:
        await insert_inventory_shortage(
            db,
            product_id=data.productId,
            current_stock=data.currentStock,
            requested_quantity=data.requestedQuantity,
            occurred_at=data.occurredAt,
        )
    logger.warning(
        "evento_inventory_shortage productId=%s stockActual=%d solicitado=%d correlationId=%s",
        data.productId,
        data.currentStock,
        data.requestedQuantity,
        correlation_id,
    )


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_shipment_delivered(payload: dict, correlation_id: str) -> None:
    """Guarda la entrega en shipment_delivery_log para las métricas de despacho."""
    data = ShipmentDeliveredPayload(**payload)

    # delivery_time_minutes se deja en None: el payload de ShipmentDelivered no trae la
    # fecha del pedido, así que el tiempo de entrega se calcula en el recálculo batch
    # (sugerencia 1.1 de Fran). El envío igual queda contado en el total de entregas.
    async with AsyncSessionLocal() as db:
        await insert_shipment_delivery(
            db,
            shipment_id=data.shipment_id,
            order_id=data.order_id,
            delivered_at=data.delivered_at,
            city=data.city,
        )

    logger.info(
        "evento_shipment_delivered envioId=%s pedidoId=%s ciudad=%s correlationId=%s",
        data.shipment_id,
        data.order_id,
        data.city,
        correlation_id,
    )


# Mapa de tipo de evento a su handler correspondiente
_HANDLERS = {
    "OrderCreated": _handle_order_created,
    "PaymentApproved": _handle_payment_approved,
    "InventoryShortage": _handle_inventory_shortage,
    "ShipmentDelivered": _handle_shipment_delivered,
}


def _make_callback(loop: asyncio.AbstractEventLoop):
    """
    Genera la función de callback para el cliente de Pub/Sub.

    El cliente de Pub/Sub opera en un hilo separado, por lo que se usa
    run_coroutine_threadsafe para despachar al event loop principal de asyncio.
    """

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
                logger.warning("tipo_evento_desconocido tipo=%s", envelope.eventType)
                message.ack()
        except Exception:
            logger.exception("error_callback_pubsub message_id=%s", message.message_id)
            message.nack()

    return callback


async def start_consumers() -> list:
    """Inicia la suscripción a las cuatro colas de Pub/Sub y retorna los futures activos."""
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
        logger.info("suscripcion_pubsub_activa suscripcion=%s", sub)

    return futures


async def stop_consumers(futures: list) -> None:
    """Cancela todos los futures de suscripción activos al apagar el servicio."""
    for future in futures:
        future.cancel()
