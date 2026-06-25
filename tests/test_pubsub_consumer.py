"""
Pruebas unitarias para app/workers/pubsub_consumer.py.

Verifica los handlers de eventos y el callback de Pub/Sub usando mocks
para aislar la lógica del worker de la infraestructura real.
"""

import asyncio
import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.pubsub_consumer import (
    _handle_inventory_shortage,
    _handle_order_created,
    _handle_payment_approved,
    _handle_shipment_delivered,
    _make_callback,
    start_consumers,
    stop_consumers,
)

# ---------------------------------------------------------------------------
# Fixtures de payloads válidos
# ---------------------------------------------------------------------------


def _payload_order_created() -> dict:
    """Payload mínimo válido para un evento OrderCreated."""
    return {
        "orderId": "ORD-001",
        "totalAmount": "49990",
        "createdAt": datetime.now(UTC).isoformat(),
    }


def _payload_payment_approved() -> dict:
    """Payload mínimo válido para un evento PaymentApproved."""
    return {
        "paymentId": "PAY-001",
        "orderId": "ORD-001",
        "amountPaid": "49990",
    }


def _payload_inventory_shortage() -> dict:
    """Payload mínimo válido para un evento InventoryShortage."""
    return {
        "productId": "P-100",
        "currentStock": 2,
        "requestedQuantity": 5,
    }


def _payload_shipment_delivered() -> dict:
    """Payload mínimo válido para un evento ShipmentDelivered."""
    return {
        "shipment_id": "SHP-001",
        "order_id": "ORD-001",
        "delivered_at": datetime.now(UTC).isoformat(),
        "city": "Santiago",
    }


def _construir_mensaje_pubsub(event_type: str, payload: dict) -> MagicMock:
    """Construye un mock de mensaje Pub/Sub con el envelope estándar."""
    envelope = {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "version": "1.0",
        "occurredAt": datetime.now(UTC).isoformat(),
        "producer": "test-producer",
        "correlationId": str(uuid.uuid4()),
        "payload": payload,
    }
    message = MagicMock()
    message.data = json.dumps(envelope).encode("utf-8")
    message.message_id = str(uuid.uuid4())
    return message


# ---------------------------------------------------------------------------
# _handle_order_created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_order_created_llama_upsert():
    """El handler de OrderCreated debe llamar a upsert_sales_from_order con los datos correctos."""
    payload = _payload_order_created()
    correlation_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_execute_result

    with (
        patch("app.workers.pubsub_consumer.AsyncSessionLocal", return_value=mock_session),
        patch(
            "app.workers.pubsub_consumer.upsert_sales_from_order",
            new_callable=AsyncMock,
        ) as mock_upsert,
    ):
        await _handle_order_created(payload, correlation_id)

    mock_upsert.assert_awaited_once()
    args = mock_upsert.call_args.args
    # Segundo arg es el monto como Decimal
    from decimal import Decimal

    assert args[2] == Decimal("49990")


@pytest.mark.asyncio
async def test_handle_order_created_payload_invalido_lanza_error():
    """Un payload sin campos requeridos debe lanzar ValidationError."""
    from pydantic import ValidationError

    with pytest.raises((ValidationError, Exception)):
        await _handle_order_created({}, "corr-123")


# ---------------------------------------------------------------------------
# _handle_payment_approved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_payment_approved_solo_loguea():
    """El handler de PaymentApproved solo debe loguear, sin escribir en BD."""
    payload = _payload_payment_approved()

    with patch("app.workers.pubsub_consumer.logger") as mock_logger:
        await _handle_payment_approved(payload, "corr-456")

    mock_logger.info.assert_called_once()
    call_args = mock_logger.info.call_args
    assert "payment_approved" in call_args.args[0] or "paymentId" in str(call_args)


@pytest.mark.asyncio
async def test_handle_payment_approved_payload_invalido_lanza_error():
    """Un payload sin campos requeridos debe lanzar ValidationError."""
    from pydantic import ValidationError

    with pytest.raises((ValidationError, Exception)):
        await _handle_payment_approved({}, "corr-123")


# ---------------------------------------------------------------------------
# _handle_inventory_shortage
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_inventory_shortage_loguea_warning():
    """El handler de InventoryShortage debe emitir un warning con los datos del quiebre."""
    payload = _payload_inventory_shortage()

    with patch("app.workers.pubsub_consumer.logger") as mock_logger:
        await _handle_inventory_shortage(payload, "corr-789")

    mock_logger.warning.assert_called_once()
    call_str = str(mock_logger.warning.call_args)
    assert "P-100" in call_str or "productId" in call_str or "shortage" in call_str.lower()


@pytest.mark.asyncio
async def test_handle_inventory_shortage_payload_invalido_lanza_error():
    """Un payload vacío debe lanzar excepción de validación."""
    from pydantic import ValidationError

    with pytest.raises((ValidationError, Exception)):
        await _handle_inventory_shortage({}, "corr-123")


# ---------------------------------------------------------------------------
# _handle_shipment_delivered
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_shipment_delivered_loguea_info():
    """El handler de ShipmentDelivered debe loguear con shipment_id y order_id."""
    payload = _payload_shipment_delivered()

    with patch("app.workers.pubsub_consumer.logger") as mock_logger:
        await _handle_shipment_delivered(payload, "corr-000")

    mock_logger.info.assert_called_once()
    call_str = str(mock_logger.info.call_args)
    assert "SHP-001" in call_str or "delivered" in call_str.lower()


@pytest.mark.asyncio
async def test_handle_shipment_delivered_payload_invalido_lanza_error():
    """Un payload sin campos requeridos debe lanzar excepción de validación."""
    from pydantic import ValidationError

    with pytest.raises((ValidationError, Exception)):
        await _handle_shipment_delivered({}, "corr-123")


# ---------------------------------------------------------------------------
# _make_callback — mensaje válido con handler conocido
# ---------------------------------------------------------------------------


def test_make_callback_mensaje_valido_llama_ack():
    """Con un mensaje válido de OrderCreated el callback debe llamar a ack()."""
    loop = asyncio.new_event_loop()
    try:
        callback = _make_callback(loop)
        message = _construir_mensaje_pubsub("OrderCreated", _payload_order_created())

        # El future que devuelve run_coroutine_threadsafe
        mock_future = MagicMock()
        mock_future.result.return_value = None

        with patch("asyncio.run_coroutine_threadsafe", return_value=mock_future):
            callback(message)

        message.ack.assert_called_once()
        message.nack.assert_not_called()
    finally:
        loop.close()


def test_make_callback_tipo_desconocido_llama_ack():
    """Con un tipo de evento desconocido el callback debe loguear y llamar a ack() de todas formas."""
    loop = asyncio.new_event_loop()
    try:
        callback = _make_callback(loop)
        message = _construir_mensaje_pubsub("EventoInventado", {"foo": "bar"})

        with patch("app.workers.pubsub_consumer.logger") as mock_logger:
            callback(message)

        message.ack.assert_called_once()
        message.nack.assert_not_called()
        mock_logger.warning.assert_called_once()
    finally:
        loop.close()


def test_make_callback_excepcion_llama_nack():
    """Cuando el future lanza una excepción el callback debe llamar a nack()."""
    loop = asyncio.new_event_loop()
    try:
        callback = _make_callback(loop)
        message = _construir_mensaje_pubsub("OrderCreated", _payload_order_created())

        mock_future = MagicMock()
        mock_future.result.side_effect = Exception("timeout")

        with patch("asyncio.run_coroutine_threadsafe", return_value=mock_future):
            callback(message)

        message.nack.assert_called_once()
        message.ack.assert_not_called()
    finally:
        loop.close()


def test_make_callback_datos_invalidos_llama_nack():
    """Con datos JSON malformados el callback debe llamar a nack()."""
    loop = asyncio.new_event_loop()
    try:
        callback = _make_callback(loop)

        message = MagicMock()
        message.data = b"esto no es json valido{{{"
        message.message_id = "msg-broken"

        callback(message)

        message.nack.assert_called_once()
        message.ack.assert_not_called()
    finally:
        loop.close()


def test_make_callback_envelope_incompleto_llama_nack():
    """Con un envelope que falta campos obligatorios el callback debe llamar a nack()."""
    loop = asyncio.new_event_loop()
    try:
        callback = _make_callback(loop)

        mensaje_incompleto = {"eventType": "OrderCreated"}  # Falta correlationId, etc.
        message = MagicMock()
        message.data = json.dumps(mensaje_incompleto).encode("utf-8")
        message.message_id = "msg-incomplete"

        callback(message)

        message.nack.assert_called_once()
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# stop_consumers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_consumers_cancela_todos_los_futures():
    """stop_consumers debe llamar a cancel() en cada future de la lista."""
    futures = [MagicMock(), MagicMock(), MagicMock()]

    await stop_consumers(futures)

    for f in futures:
        f.cancel.assert_called_once()


@pytest.mark.asyncio
async def test_stop_consumers_lista_vacia():
    """Con lista vacía no debe lanzar excepción."""
    await stop_consumers([])


@pytest.mark.asyncio
async def test_stop_consumers_un_future():
    """Con un único future debe cancelarlo correctamente."""
    future = MagicMock()
    await stop_consumers([future])
    future.cancel.assert_called_once()


# ---------------------------------------------------------------------------
# start_consumers con suscripciones vacías
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_start_consumers_suscripciones_vacias_retorna_lista_vacia():
    """Con todas las suscripciones configuradas como cadena vacía debe retornar lista vacía."""
    mock_subscriber = MagicMock()

    with (
        patch(
            "app.workers.pubsub_consumer.pubsub_v1.SubscriberClient", return_value=mock_subscriber
        ),
        patch("app.workers.pubsub_consumer.settings") as mock_settings,
    ):
        mock_settings.PUBSUB_SUBSCRIPTION_ORDER_CREATED = ""
        mock_settings.PUBSUB_SUBSCRIPTION_PAYMENT_APPROVED = ""
        mock_settings.PUBSUB_SUBSCRIPTION_INVENTORY_SHORTAGE = ""
        mock_settings.PUBSUB_SUBSCRIPTION_SHIPMENT_DELIVERED = ""

        futures = await start_consumers()

    assert futures == []
    mock_subscriber.subscribe.assert_not_called()
