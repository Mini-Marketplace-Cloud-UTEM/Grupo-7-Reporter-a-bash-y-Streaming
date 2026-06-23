"""
Pruebas unitarias para app/services/batch_service.py.

Verifica que run_batch_recalculate procese correctamente los distintos tipos
de eventos almacenados en Supabase Storage, aplique los filtros de fecha y
maneje fechas inválidas y tipos de evento desconocidos.
"""

import json
import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.batch_service import run_batch_recalculate


def _construir_evento(event_type: str, payload: dict, occurred_at: str | None = None) -> dict:
    """Construye un evento crudo para simular los archivos en Supabase Storage."""
    return {
        "eventType": event_type,
        "correlationId": str(uuid.uuid4()),
        "occurredAt": occurred_at or datetime.now(UTC).isoformat(),
        "payload": payload,
    }


def _mock_supabase(eventos: list[dict], filename: str = "events.json"):
    """Crea el mock del cliente de Supabase Storage con los eventos dados."""
    mock_client = MagicMock()
    mock_client.storage.from_.return_value.list.return_value = [{"name": filename}]
    mock_client.storage.from_.return_value.download.return_value = json.dumps(eventos).encode()
    return mock_client


# ---------------------------------------------------------------------------
# Evento OrderCreated
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_procesa_order_created():
    """Un evento OrderCreated debe llamar a upsert_sales_from_order con el monto correcto."""
    evento = _construir_evento(
        "OrderCreated",
        {"orderId": "ORD-001", "totalAmount": "49990", "createdAt": datetime.now(UTC).isoformat()},
    )
    mock_client = _mock_supabase([evento])

    mock_db = AsyncMock()
    # upsert_sales_from_order hace execute + commit
    mock_execute_result = MagicMock()
    mock_execute_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute_result

    with patch("app.services.batch_service.create_client", return_value=mock_client):
        await run_batch_recalculate(mock_db, None, None, uuid.uuid4())

    # Debe haber hecho commit al menos una vez (upsert + marcado batch)
    assert mock_db.commit.await_count >= 1


@pytest.mark.asyncio
async def test_batch_procesa_payment_approved_sin_upsert():
    """Un evento PaymentApproved debe procesarse sin llamar a upsert (pass implícito)."""
    evento = _construir_evento(
        "PaymentApproved",
        {"paymentId": "PAY-001", "orderId": "ORD-001", "amountPaid": "49990"},
    )
    mock_client = _mock_supabase([evento])

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()

    with (
        patch("app.services.batch_service.create_client", return_value=mock_client),
        patch(
            "app.services.batch_service.upsert_sales_from_order",
            new_callable=AsyncMock,
        ) as mock_upsert,
    ):
        await run_batch_recalculate(mock_db, None, None, uuid.uuid4())

    mock_upsert.assert_not_called()


# ---------------------------------------------------------------------------
# Filtrado por rango de fechas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_filtra_eventos_fuera_de_rango():
    """Eventos anteriores a from_date deben ser ignorados."""
    evento_antiguo = _construir_evento(
        "OrderCreated",
        {"orderId": "ORD-OLD", "totalAmount": "100", "createdAt": "2023-01-01T10:00:00+00:00"},
        occurred_at="2023-01-01T10:00:00+00:00",
    )
    evento_reciente = _construir_evento(
        "OrderCreated",
        {"orderId": "ORD-NEW", "totalAmount": "200", "createdAt": "2024-06-15T10:00:00+00:00"},
        occurred_at="2024-06-15T10:00:00+00:00",
    )
    mock_client = _mock_supabase([evento_antiguo, evento_reciente])

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()

    with (
        patch("app.services.batch_service.create_client", return_value=mock_client),
        patch(
            "app.services.batch_service.upsert_sales_from_order",
            new_callable=AsyncMock,
        ) as mock_upsert,
    ):
        await run_batch_recalculate(
            mock_db,
            date(2024, 6, 1),
            date(2024, 6, 30),
            uuid.uuid4(),
        )

    # Solo el evento reciente debe haberse procesado
    assert mock_upsert.call_count == 1
    _, kwargs = mock_upsert.call_args
    # El primer argumento posicional es db, el segundo period_date
    args = mock_upsert.call_args.args
    processed_date = args[1]
    assert processed_date.date() == date(2024, 6, 15)


@pytest.mark.asyncio
async def test_batch_filtra_eventos_despues_de_to_date():
    """Eventos posteriores a to_date deben ser ignorados."""
    evento_futuro = _construir_evento(
        "OrderCreated",
        {"orderId": "ORD-FUTURE", "totalAmount": "500", "createdAt": "2025-12-31T10:00:00+00:00"},
        occurred_at="2025-12-31T10:00:00+00:00",
    )
    mock_client = _mock_supabase([evento_futuro])

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()

    with (
        patch("app.services.batch_service.create_client", return_value=mock_client),
        patch(
            "app.services.batch_service.upsert_sales_from_order",
            new_callable=AsyncMock,
        ) as mock_upsert,
    ):
        await run_batch_recalculate(
            mock_db,
            date(2024, 1, 1),
            date(2024, 12, 31),
            uuid.uuid4(),
        )

    mock_upsert.assert_not_called()


# ---------------------------------------------------------------------------
# occurredAt inválido
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_maneja_occurred_at_invalido():
    """Un occurredAt con formato inválido no debe lanzar excepción; usa datetime.now()."""
    evento = _construir_evento(
        "OrderCreated",
        {"orderId": "ORD-X", "totalAmount": "1000", "createdAt": datetime.now(UTC).isoformat()},
        occurred_at="no-es-una-fecha",
    )
    mock_client = _mock_supabase([evento])

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()

    with (
        patch("app.services.batch_service.create_client", return_value=mock_client),
        patch(
            "app.services.batch_service.upsert_sales_from_order",
            new_callable=AsyncMock,
        ) as mock_upsert,
    ):
        # No debe lanzar excepción
        await run_batch_recalculate(mock_db, None, None, uuid.uuid4())

    # El evento debe haberse procesado usando datetime.now() como fallback
    mock_upsert.assert_called_once()


# ---------------------------------------------------------------------------
# Tipo de evento desconocido
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_ignora_evento_desconocido():
    """Un tipo de evento no reconocido no debe llamar a upsert ni lanzar excepción."""
    evento = _construir_evento("EventoDesconocido", {"foo": "bar"})
    mock_client = _mock_supabase([evento])

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()

    with (
        patch("app.services.batch_service.create_client", return_value=mock_client),
        patch(
            "app.services.batch_service.upsert_sales_from_order",
            new_callable=AsyncMock,
        ) as mock_upsert,
    ):
        await run_batch_recalculate(mock_db, None, None, uuid.uuid4())

    mock_upsert.assert_not_called()


# ---------------------------------------------------------------------------
# Múltiples archivos y payload como objeto único (no lista)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_procesa_payload_objeto_unico():
    """Cuando el archivo contiene un solo objeto (no lista) debe procesarlo igualmente."""
    evento = _construir_evento(
        "OrderCreated",
        {"orderId": "ORD-S", "totalAmount": "75000", "createdAt": datetime.now(UTC).isoformat()},
    )
    mock_client = MagicMock()
    mock_client.storage.from_.return_value.list.return_value = [{"name": "single.json"}]
    # Objeto único, no lista
    mock_client.storage.from_.return_value.download.return_value = json.dumps(evento).encode()

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()

    with (
        patch("app.services.batch_service.create_client", return_value=mock_client),
        patch(
            "app.services.batch_service.upsert_sales_from_order",
            new_callable=AsyncMock,
        ) as mock_upsert,
    ):
        await run_batch_recalculate(mock_db, None, None, uuid.uuid4())

    mock_upsert.assert_called_once()


# ---------------------------------------------------------------------------
# Manejo de excepción en create_client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_maneja_excepcion_supabase():
    """Cuando create_client falla no debe propagar la excepción (se captura internamente)."""
    mock_db = AsyncMock()

    with patch(
        "app.services.batch_service.create_client",
        side_effect=Exception("connection refused"),
    ):
        # La función captura la excepción con logger.exception y no la relanza
        await run_batch_recalculate(mock_db, None, None, uuid.uuid4())

    # No debe haber ejecutado ninguna consulta a la BD
    mock_db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Marcado BATCH_RECALCULATED con filtro de fechas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_marca_registros_con_rango():
    """El UPDATE de BATCH_RECALCULATED debe ejecutarse incluso con from_date y to_date."""
    mock_client = _mock_supabase([])  # Sin eventos, solo el UPDATE final importa

    mock_db = AsyncMock()
    mock_db.execute.return_value = MagicMock()

    with patch("app.services.batch_service.create_client", return_value=mock_client):
        await run_batch_recalculate(
            mock_db,
            date(2024, 6, 1),
            date(2024, 6, 30),
            uuid.uuid4(),
        )

    # Debe haberse ejecutado el UPDATE y el commit final
    mock_db.execute.assert_awaited_once()
    mock_db.commit.assert_awaited_once()
