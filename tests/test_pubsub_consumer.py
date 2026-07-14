"""
Pruebas unitarias para app/workers/pubsub_consumer.py.

Verifica los handlers de eventos, el callback de Pub/Sub y la suscripción
multi-grupo (un SubscriberClient cacheado por grupo upstream, autenticado
con su propia service account) usando mocks para aislar la lógica del
worker de la infraestructura real.

Convención de eventType: UPPER_SNAKE_CASE.
Payload de ShipmentDelivered: camelCase (shipmentId, orderId, deliveredAt).
"""

import asyncio
import base64
import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.pubsub_consumer import (
    _build_credentials,
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
    """Payload mínimo válido para un evento ORDER_CREATED."""
    return {
        "orderId": "ORD-001",
        "totalAmount": "49990",
        "createdAt": datetime.now(UTC).isoformat(),
    }


def _payload_payment_approved() -> dict:
    """Payload mínimo válido para un evento PAYMENT_APPROVED."""
    return {
        "paymentId": "PAY-001",
        "orderId": "ORD-001",
        "amountPaid": "49990",
    }


def _payload_inventory_shortage() -> dict:
    """Payload mínimo válido para un evento INVENTORY_SHORTAGE."""
    return {
        "productId": "P-100",
        "currentStock": 2,
        "requestedQuantity": 5,
    }


def _payload_shipment_delivered() -> dict:
    """Payload mínimo válido para un evento SHIPMENT_DELIVERED (camelCase)."""
    return {
        "shipmentId": "SHP-001",
        "orderId": "ORD-001",
        "deliveredAt": datetime.now(UTC).isoformat(),
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
    """El handler de ORDER_CREATED debe llamar a upsert_sales_from_order y a log_order_status."""
    payload = _payload_order_created()
    correlation_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.workers.pubsub_consumer.AsyncSessionLocal", return_value=mock_session),
        patch(
            "app.workers.pubsub_consumer.upsert_sales_from_order",
            new_callable=AsyncMock,
        ) as mock_upsert,
        patch(
            "app.workers.pubsub_consumer.log_order_status",
            new_callable=AsyncMock,
        ) as mock_log_status,
    ):
        await _handle_order_created(payload, correlation_id)

    mock_upsert.assert_awaited_once()
    args = mock_upsert.call_args.args
    # Segundo arg es el monto como Decimal
    from decimal import Decimal

    assert args[2] == Decimal("49990")

    mock_log_status.assert_awaited_once()
    status_kwargs = mock_log_status.call_args.kwargs
    assert status_kwargs["order_id"] == "ORD-001"
    assert status_kwargs["status"] == "CREATED"


@pytest.mark.asyncio
async def test_handle_order_created_payload_invalido_lanza_error():
    """Un payload sin campos requeridos debe lanzar ValidationError."""
    from pydantic import ValidationError

    with pytest.raises((ValidationError, Exception)):
        await _handle_order_created({}, "corr-123")


@pytest.mark.asyncio
async def test_handle_order_created_usa_status_del_payload_cuando_presente():
    """
    Cuando el payload incluye status, log_order_status debe recibir ese valor.

    La lógica del worker es: status=data.status or "CREATED".
    Este test ejercita la rama data.status != None, que no cubren los otros tests.
    """
    payload = {
        "orderId": "ORD-002",
        "totalAmount": "29990",
        "createdAt": datetime.now(UTC).isoformat(),
        "status": "PENDING",
    }
    correlation_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.workers.pubsub_consumer.AsyncSessionLocal", return_value=mock_session),
        patch(
            "app.workers.pubsub_consumer.upsert_sales_from_order",
            new_callable=AsyncMock,
        ),
        patch(
            "app.workers.pubsub_consumer.log_order_status",
            new_callable=AsyncMock,
        ) as mock_log_status,
    ):
        await _handle_order_created(payload, correlation_id)

    mock_log_status.assert_awaited_once()
    status_kwargs = mock_log_status.call_args.kwargs
    # Debe usar el status del payload ("PENDING"), no el valor por defecto "CREATED"
    assert status_kwargs["status"] == "PENDING"
    assert status_kwargs["order_id"] == "ORD-002"


# ---------------------------------------------------------------------------
# _handle_payment_approved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_payment_approved_solo_loguea():
    """El handler de PAYMENT_APPROVED solo debe loguear, sin escribir en BD."""
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
    """El handler de INVENTORY_SHORTAGE debe emitir un warning con los datos del quiebre."""
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
async def test_handle_shipment_delivered_persiste_y_loguea():
    """El handler de SHIPMENT_DELIVERED debe persistir la entrega y loguear el evento."""
    payload = _payload_shipment_delivered()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.workers.pubsub_consumer.AsyncSessionLocal", return_value=mock_session),
        patch(
            "app.workers.pubsub_consumer.log_shipment_delivery",
            new_callable=AsyncMock,
        ) as mock_log_delivery,
        patch("app.workers.pubsub_consumer.logger") as mock_logger,
    ):
        await _handle_shipment_delivered(payload, "corr-000")

    mock_log_delivery.assert_awaited_once()
    delivery_kwargs = mock_log_delivery.call_args.kwargs
    assert delivery_kwargs["shipment_id"] == "SHP-001"
    assert delivery_kwargs["order_id"] == "ORD-001"
    assert delivery_kwargs["city"] == "Santiago"
    assert delivery_kwargs["delivery_time_minutes"] is None

    mock_logger.info.assert_called_once()
    call_str = str(mock_logger.info.call_args)
    assert "SHP-001" in call_str or "delivered" in call_str.lower()


@pytest.mark.asyncio
async def test_handle_shipment_delivered_payload_invalido_lanza_error():
    """Un payload sin campos requeridos debe lanzar excepción de validación."""
    from pydantic import ValidationError

    with pytest.raises((ValidationError, Exception)):
        await _handle_shipment_delivered({}, "corr-123")


@pytest.mark.asyncio
async def test_handle_shipment_delivered_con_city_none():
    """
    Cuando city está ausente en el payload (campo opcional), el handler
    debe pasar city=None a log_shipment_delivery sin lanzar error.

    Verifica que el campo opcional de ShipmentDeliveredPayload se propaga
    correctamente hasta la capa de persistencia.
    """
    payload = {
        "shipmentId": "SHP-002",
        "orderId": "ORD-002",
        "deliveredAt": datetime.now(UTC).isoformat(),
        # city omitido intencionalmente
    }

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    with (
        patch("app.workers.pubsub_consumer.AsyncSessionLocal", return_value=mock_session),
        patch(
            "app.workers.pubsub_consumer.log_shipment_delivery",
            new_callable=AsyncMock,
        ) as mock_log_delivery,
        patch("app.workers.pubsub_consumer.logger"),
    ):
        await _handle_shipment_delivered(payload, "corr-001")

    mock_log_delivery.assert_awaited_once()
    delivery_kwargs = mock_log_delivery.call_args.kwargs
    assert delivery_kwargs["city"] is None
    assert delivery_kwargs["shipment_id"] == "SHP-002"


# ---------------------------------------------------------------------------
# _make_callback — mensaje válido con handler conocido
# ---------------------------------------------------------------------------


def test_make_callback_mensaje_valido_llama_ack():
    """Con un mensaje válido de ORDER_CREATED el callback debe llamar a ack()."""
    loop = asyncio.new_event_loop()
    try:
        callback = _make_callback(loop)
        message = _construir_mensaje_pubsub("ORDER_CREATED", _payload_order_created())

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
        message = _construir_mensaje_pubsub("EVENTO_INVENTADO", {"foo": "bar"})

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
        message = _construir_mensaje_pubsub("ORDER_CREATED", _payload_order_created())

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

        mensaje_incompleto = {"eventType": "ORDER_CREATED"}  # Falta correlationId, etc.
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
# start_consumers — suscripción multi-grupo
# ---------------------------------------------------------------------------
# Se inyecta un _EVENT_SOURCES de prueba vía patch en vez de depender de los
# valores reales (que son placeholders temporales "pendiente-confirmar" que
# cambiarán cuando G4/G5/G8 confirmen sus subscription paths).


@pytest.mark.asyncio
async def test_start_consumers_salta_suscripciones_pendiente_confirmar():
    """Las entradas con path placeholder 'pendiente-confirmar' no deben suscribirse."""
    fake_sources = {
        "EVENTO_A": ("G4", "projects/p4/subscriptions/<pendiente-confirmar-con-g4>"),
        "EVENTO_B": ("G5", ""),
    }
    mock_subscriber = MagicMock()

    with (
        patch("app.workers.pubsub_consumer._EVENT_SOURCES", fake_sources),
        patch(
            "app.workers.pubsub_consumer.pubsub_v1.SubscriberClient", return_value=mock_subscriber
        ),
        patch("app.workers.pubsub_consumer._build_credentials", return_value=None),
    ):
        futures = await start_consumers()

    assert futures == []
    mock_subscriber.subscribe.assert_not_called()


@pytest.mark.asyncio
async def test_start_consumers_suscribe_entradas_con_path_real():
    """Una entrada con subscription path real debe suscribirse usando el SubscriberClient del grupo."""
    fake_sources = {
        "EVENTO_PENDIENTE": ("G4", "projects/p4/subscriptions/<pendiente-confirmar-con-g4>"),
        "EVENTO_REAL": ("G6", "projects/proyecto-arqui-g6/subscriptions/g7-registro-sub"),
    }
    mock_subscriber = MagicMock()
    mock_future = MagicMock()
    mock_subscriber.subscribe.return_value = mock_future

    with (
        patch("app.workers.pubsub_consumer._EVENT_SOURCES", fake_sources),
        patch(
            "app.workers.pubsub_consumer.pubsub_v1.SubscriberClient", return_value=mock_subscriber
        ),
        patch("app.workers.pubsub_consumer._build_credentials", return_value=None),
    ):
        futures = await start_consumers()

    assert futures == [mock_future]
    mock_subscriber.subscribe.assert_called_once()
    call_args = mock_subscriber.subscribe.call_args
    assert call_args.args[0] == "projects/proyecto-arqui-g6/subscriptions/g7-registro-sub"


@pytest.mark.asyncio
async def test_start_consumers_reusa_client_del_mismo_grupo():
    """Dos eventos reales del mismo grupo deben reusar el mismo SubscriberClient (no crear dos)."""
    fake_sources = {
        "EVENTO_UNO": ("G6", "projects/proyecto-arqui-g6/subscriptions/sub-uno"),
        "EVENTO_DOS": ("G6", "projects/proyecto-arqui-g6/subscriptions/sub-dos"),
    }
    mock_subscriber = MagicMock()

    with (
        patch("app.workers.pubsub_consumer._EVENT_SOURCES", fake_sources),
        patch(
            "app.workers.pubsub_consumer.pubsub_v1.SubscriberClient", return_value=mock_subscriber
        ) as mock_client_cls,
        patch("app.workers.pubsub_consumer._build_credentials", return_value=None),
    ):
        futures = await start_consumers()

    assert len(futures) == 2
    mock_client_cls.assert_called_once()
    assert mock_subscriber.subscribe.call_count == 2


# ---------------------------------------------------------------------------
# _build_credentials
# ---------------------------------------------------------------------------


def test_build_credentials_sin_contenido_retorna_none_y_loguea_warning():
    """Si la variable de settings del grupo está vacía debe retornar None y loguear warning."""
    with (
        patch("app.workers.pubsub_consumer.settings") as mock_settings,
        patch("app.workers.pubsub_consumer.logger") as mock_logger,
    ):
        mock_settings.G6_GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY_CONTENT = ""

        result = _build_credentials("G6")

    assert result is None
    mock_logger.warning.assert_called_once()


def test_build_credentials_contenido_valido_retorna_credenciales():
    """Con base64 válido debe decodificar el JSON y construir las credenciales."""
    key_data = {"type": "service_account", "project_id": "proyecto-arqui-g6"}
    raw_b64 = base64.b64encode(json.dumps(key_data).encode("utf-8")).decode("utf-8")
    mock_credentials = MagicMock()

    with (
        patch("app.workers.pubsub_consumer.settings") as mock_settings,
        patch(
            "app.workers.pubsub_consumer.service_account.Credentials.from_service_account_info",
            return_value=mock_credentials,
        ) as mock_from_info,
    ):
        mock_settings.G6_GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY_CONTENT = raw_b64

        result = _build_credentials("G6")

    assert result is mock_credentials
    mock_from_info.assert_called_once()
    assert mock_from_info.call_args.args[0] == key_data


def test_build_credentials_contenido_invalido_retorna_none_y_loguea_exception():
    """Con contenido que no decodifica a JSON válido debe retornar None y loguear exception."""
    with (
        patch("app.workers.pubsub_consumer.settings") as mock_settings,
        patch("app.workers.pubsub_consumer.logger") as mock_logger,
    ):
        mock_settings.G4_GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY_CONTENT = "esto-no-es-base64-valido{{{"

        result = _build_credentials("G4")

    assert result is None
    mock_logger.exception.assert_called_once()


def test_build_credentials_usa_la_variable_del_grupo_correcto():
    """Debe leer settings.<GRUPO>_GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY_CONTENT, no la de otro grupo."""
    key_data_g6 = {"project_id": "proyecto-g6"}
    key_data_g4 = {"project_id": "proyecto-g4"}
    raw_g6 = base64.b64encode(json.dumps(key_data_g6).encode("utf-8")).decode("utf-8")
    raw_g4 = base64.b64encode(json.dumps(key_data_g4).encode("utf-8")).decode("utf-8")

    with (
        patch("app.workers.pubsub_consumer.settings") as mock_settings,
        patch(
            "app.workers.pubsub_consumer.service_account.Credentials.from_service_account_info",
            side_effect=lambda data, scopes: data,
        ),
    ):
        mock_settings.G6_GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY_CONTENT = raw_g6
        mock_settings.G4_GOOGLE_CLOUD_SERVICE_ACCOUNT_KEY_CONTENT = raw_g4

        assert _build_credentials("G6") == key_data_g6
        assert _build_credentials("G4") == key_data_g4
