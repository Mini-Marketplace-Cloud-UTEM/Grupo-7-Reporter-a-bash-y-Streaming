"""
Worker de consumo de eventos desde Google Cloud Pub/Sub.

Cada tipo de evento es publicado por un grupo upstream distinto, con su propio
proyecto GCP y su propia service account (ver _EVENT_SOURCES). Por eso se
autentica con múltiples service accounts y se mantiene un SubscriberClient por
grupo (cacheado, no uno por evento). Cada mensaje se despacha al handler
correspondiente según el campo eventType del envelope estándar.
Implementa reintentos con Exponential Backoff (máximo 5 intentos) usando tenacity.

Convención de eventType: UPPER_SNAKE_CASE (ej: ORDER_CREATED, SHIPMENT_DELIVERED).
"""

import asyncio
import base64
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

from google.cloud import pubsub_v1
from google.oauth2 import service_account
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
    log_order_status,
    log_shipment_delivery,
    upsert_sales_from_order,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)

_PUBSUB_SCOPES = ["https://www.googleapis.com/auth/pubsub"]

# Mapa de eventType -> (grupo upstream, subscription path completo).
# Cada grupo publica desde su propio proyecto GCP con su propia service account.
# Los subscription IDs marcados como "pendiente-confirmar" son placeholders:
# actualizar cuando el grupo correspondiente confirme el path real.
_EVENT_SOURCES: dict[str, tuple[str, str]] = {
    "ORDER_CREATED": (
        "G5",
        "projects/proyecto-arqui-g5/subscriptions/<pendiente-confirmar-con-g5>",
    ),
    "INVENTORY_SHORTAGE": (
        "G4",
        "projects/proyecto-arqui-g4/subscriptions/<pendiente-confirmar-con-g4>",
    ),
    "PAYMENT_APPROVED": ("G8","projects/project-76891426-ab92-49ba-b24/subscriptions/g7-payment-events-sub"),
    "SHIPMENT_DELIVERED": ("G6", "projects/proyecto-arqui-g6/subscriptions/g7-registro-sub"),
}


def _build_credentials(group: str) -> service_account.Credentials | None:
    """Decodifica la service account key (base64 → JSON) del grupo dado y retorna credenciales."""
    raw = getattr(settings, f"{group}_GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY_CONTENT")
    if not raw:
        logger.warning(
            "credenciales_gcp_no_configuradas grupo=%s — se usará ADC como fallback", group
        )
        return None
    try:
        key_data = json.loads(base64.b64decode(raw))
        return service_account.Credentials.from_service_account_info(
            key_data, scopes=_PUBSUB_SCOPES
        )
    except Exception:
        logger.exception(
            "error_decodificando_credenciales_gcp grupo=%s — se usará ADC como fallback", group
        )
        return None


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_order_created(payload: dict, correlation_id: str) -> None:
    """Acumula las ventas del pedido en fact_sales_summary y registra el estado inicial en order_status_log."""
    data = OrderCreatedPayload(**payload)
    async with AsyncSessionLocal() as db:
        await upsert_sales_from_order(
            db, data.createdAt, Decimal(str(data.totalAmount)), correlation_id
        )
        await log_order_status(
            db,
            order_id=data.orderId,
            status=data.status or "CREATED",
            occurred_at=data.createdAt,
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
    """Registra la alerta de quiebre de stock para análisis posterior."""
    data = InventoryShortagePayload(**payload)
    logger.warning(
        "evento_inventory_shortage productId=%s stockActual=%d solicitado=%d correlationId=%s",
        data.productId,
        data.currentStock,
        data.requestedQuantity,
        correlation_id,
    )


@retry(wait=wait_exponential(multiplier=1, min=2, max=30), stop=stop_after_attempt(5), reraise=True)
async def _handle_shipment_delivered(payload: dict, correlation_id: str) -> None:
    """Persiste la entrega del envío en shipment_delivery_log y loguea el evento."""
    data = ShipmentDeliveredPayload(**payload)
    async with AsyncSessionLocal() as db:
        await log_shipment_delivery(
            db,
            shipment_id=data.shipmentId,
            order_id=data.orderId,
            delivered_at=data.deliveredAt,
            city=data.city,
            delivery_time_minutes=None,  # el payload de SHIPMENT_DELIVERED no incluye este campo
        )
    logger.info(
        "evento_shipment_delivered envioId=%s pedidoId=%s ciudad=%s correlationId=%s",
        data.shipmentId,
        data.orderId,
        data.city,
        correlation_id,
    )


# Mapa de tipo de evento (UPPER_SNAKE_CASE) a su handler correspondiente
_HANDLERS = {
    "ORDER_CREATED": _handle_order_created,
    "PAYMENT_APPROVED": _handle_payment_approved,
    "INVENTORY_SHORTAGE": _handle_inventory_shortage,
    "SHIPMENT_DELIVERED": _handle_shipment_delivered,
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
    """Inicia la suscripción a las colas de Pub/Sub de cada grupo y retorna los futures activos."""
    loop = asyncio.get_running_loop()
    callback = _make_callback(loop)

    # Un SubscriberClient por grupo (cacheado), no uno por evento.
    clients: dict[str, pubsub_v1.SubscriberClient] = {}

    futures = []
    for event_type, (group, sub) in _EVENT_SOURCES.items():
        if not sub or "pendiente-confirmar" in sub:
            logger.warning("suscripcion_pendiente_confirmar grupo=%s evento=%s", group, event_type)
            continue

        if group not in clients:
            credentials = _build_credentials(group)
            clients[group] = pubsub_v1.SubscriberClient(credentials=credentials)

        future = clients[group].subscribe(sub, callback=callback)
        futures.append(future)
        logger.info("suscripcion_pubsub_activa grupo=%s suscripcion=%s", group, sub)

    return futures


async def stop_consumers(futures: list) -> None:
    """Cancela todos los futures de suscripción activos al apagar el servicio."""
    for future in futures:
        future.cancel()
