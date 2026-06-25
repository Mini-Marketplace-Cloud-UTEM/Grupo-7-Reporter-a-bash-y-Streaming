"""
Pruebas de integración para los endpoints de la API de Reportería.

Verifica que cada ruta respete el contrato OpenAPI:
paths, códigos HTTP, validación de headers obligatorios y estructura de respuesta.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# Headers mínimos requeridos por todos los endpoints
HEADERS = {
    "X-Request-Id": str(uuid.uuid4()),
    "X-Correlation-Id": str(uuid.uuid4()),
    "X-Consumer": "group-01",
}


@pytest.fixture
async def client():
    """Cliente HTTP asíncrono apuntando a la aplicación FastAPI en modo test."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    """El endpoint de salud debe responder 200 sin headers."""
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_reporte_ventas_sin_headers(client):
    """Sin headers obligatorios el endpoint debe retornar 422."""
    r = await client.get("/reports/sales")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_reporte_ventas_ok(client):
    """Con headers válidos el endpoint de ventas debe retornar 200."""
    mock_report = {
        "period": {"from": None, "to": None},
        "totalSales": 100000,
        "totalOrders": 5,
        "currency": "CLP",
    }
    with patch(
        "app.api.routes.reports.analytics_service.get_sales_report",
        new_callable=AsyncMock,
        return_value=mock_report,
    ):
        r = await client.get("/reports/sales", headers=HEADERS)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_recalculo_batch_sin_idempotency(client):
    """Sin Idempotency-Key el endpoint de recálculo debe retornar 422."""
    r = await client.post("/reports/batch/recalculate", headers=HEADERS)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_recalculo_batch_ok(client):
    """Con todos los headers el recálculo debe retornar 202 con jobId y status QUEUED."""
    headers = {**HEADERS, "Idempotency-Key": str(uuid.uuid4())}
    with patch("app.api.routes.batch.run_batch_recalculate", new_callable=AsyncMock):
        r = await client.post("/reports/batch/recalculate", headers=headers, json={})
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "QUEUED"
    assert "jobId" in body


# ---------------------------------------------------------------------------
# GET /reports/orders-by-status
# ---------------------------------------------------------------------------

mock_orders = [
    {"status": "DELIVERED", "count": 198},
    {"status": "PENDING", "count": 31},
]


@pytest.mark.asyncio
async def test_orders_by_status_sin_headers(client):
    """Sin headers obligatorios debe retornar 422."""
    r = await client.get("/reports/orders-by-status")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_orders_by_status_ok(client):
    """Con headers válidos debe retornar 200 y una lista de objetos con status y count."""
    with patch(
        "app.api.routes.reports.analytics_service.get_orders_by_status",
        new_callable=AsyncMock,
        return_value=mock_orders,
    ):
        r = await client.get("/reports/orders-by-status", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert body[0]["status"] == "DELIVERED"
    assert "count" in body[0]


# ---------------------------------------------------------------------------
# GET /reports/top-products
# ---------------------------------------------------------------------------

mock_top_products = {
    "data": [{"productId": "P-100", "unitsSold": 85, "revenue": 4_250_000, "name": None}],
    "pagination": {"totalItems": 1, "totalPages": 1, "currentPage": 1, "pageSize": 20},
}


@pytest.mark.asyncio
async def test_top_products_sin_headers(client):
    """Sin headers obligatorios debe retornar 422."""
    r = await client.get("/reports/top-products")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_top_products_ok(client):
    """Con headers válidos debe retornar 200 con campos data y pagination."""
    with patch(
        "app.api.routes.reports.analytics_service.get_top_products",
        new_callable=AsyncMock,
        return_value=mock_top_products,
    ):
        r = await client.get("/reports/top-products", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "data" in body
    assert "pagination" in body


@pytest.mark.asyncio
async def test_top_products_page_cero_invalido(client):
    """page=0 viola la restricción ge=1 y debe retornar 422."""
    r = await client.get("/reports/top-products?page=0", headers=HEADERS)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_top_products_page_size_cero_invalido(client):
    """pageSize=0 viola la restricción ge=1 y debe retornar 422."""
    r = await client.get("/reports/top-products?pageSize=0", headers=HEADERS)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_top_products_page_size_mayor_100_invalido(client):
    """pageSize=101 viola la restricción le=100 y debe retornar 422."""
    r = await client.get("/reports/top-products?pageSize=101", headers=HEADERS)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_top_products_paginado_ok(client):
    """Con page=2 y pageSize=5 debe retornar 200."""
    with patch(
        "app.api.routes.reports.analytics_service.get_top_products",
        new_callable=AsyncMock,
        return_value=mock_top_products,
    ):
        r = await client.get("/reports/top-products?page=2&pageSize=5", headers=HEADERS)
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# GET /reports/average-ticket
# ---------------------------------------------------------------------------

mock_avg_ticket = {"averageTicket": 79647, "currency": "CLP"}


@pytest.mark.asyncio
async def test_average_ticket_sin_headers(client):
    """Sin headers obligatorios debe retornar 422."""
    r = await client.get("/reports/average-ticket")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_average_ticket_ok(client):
    """Con headers válidos debe retornar 200 con campo averageTicket."""
    with patch(
        "app.api.routes.reports.analytics_service.get_average_ticket",
        new_callable=AsyncMock,
        return_value=mock_avg_ticket,
    ):
        r = await client.get("/reports/average-ticket", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "averageTicket" in body


# ---------------------------------------------------------------------------
# GET /reports/peak-hours
# ---------------------------------------------------------------------------

mock_peak_hours = [{"hour": 18, "orderCount": 71}]


@pytest.mark.asyncio
async def test_peak_hours_sin_headers(client):
    """Sin headers obligatorios debe retornar 422."""
    r = await client.get("/reports/peak-hours")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_peak_hours_ok(client):
    """Con headers válidos debe retornar 200 con una lista de objetos hour/orderCount."""
    with patch(
        "app.api.routes.reports.analytics_service.get_peak_hours",
        new_callable=AsyncMock,
        return_value=mock_peak_hours,
    ):
        r = await client.get("/reports/peak-hours", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert isinstance(body, list)
    assert body[0]["hour"] == 18
    assert "orderCount" in body[0]


# ---------------------------------------------------------------------------
# GET /reports/delivery-performance
# ---------------------------------------------------------------------------

mock_delivery = {"avgDeliveryTimeMinutes": 138, "totalDeliveredCount": 198}


@pytest.mark.asyncio
async def test_delivery_performance_sin_headers(client):
    """Sin headers obligatorios debe retornar 422."""
    r = await client.get("/reports/delivery-performance")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_delivery_performance_ok(client):
    """Con headers válidos debe retornar 200 con avgDeliveryTimeMinutes y totalDeliveredCount."""
    with patch(
        "app.api.routes.reports.analytics_service.get_delivery_performance",
        new_callable=AsyncMock,
        return_value=mock_delivery,
    ):
        r = await client.get("/reports/delivery-performance", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert "avgDeliveryTimeMinutes" in body
    assert "totalDeliveredCount" in body


# ---------------------------------------------------------------------------
# GET /reports/sales con parámetros de fecha
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reporte_ventas_con_fechas_ok(client):
    """Con from y to válidos debe retornar 200."""
    mock_report = {
        "period": {"from": "2024-01-01", "to": "2024-01-31"},
        "totalSales": 24_850_000,
        "totalOrders": 312,
        "currency": "CLP",
    }
    with patch(
        "app.api.routes.reports.analytics_service.get_sales_report",
        new_callable=AsyncMock,
        return_value=mock_report,
    ):
        r = await client.get("/reports/sales?from=2024-01-01&to=2024-01-31", headers=HEADERS)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_reporte_ventas_fecha_invalida(client):
    """Con una fecha no parseable en from debe retornar 422."""
    r = await client.get("/reports/sales?from=no-es-fecha", headers=HEADERS)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /reports/batch/recalculate con body de fechas
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recalculo_batch_con_body_fechas(client):
    """Con body que incluye from y to debe retornar 202."""
    headers = {**HEADERS, "Idempotency-Key": str(uuid.uuid4())}
    with patch("app.api.routes.batch.run_batch_recalculate", new_callable=AsyncMock):
        r = await client.post(
            "/reports/batch/recalculate",
            headers=headers,
            json={"from": "2024-01-01", "to": "2024-01-31"},
        )
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "QUEUED"
    assert "jobId" in body


# ---------------------------------------------------------------------------
# Validación de UUID inválido en headers (debe retornar 400, no 422)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reporte_ventas_request_id_invalido(client):
    """X-Request-Id con valor no UUID debe retornar 400 con código INVALID_HEADER."""
    headers = {**HEADERS, "X-Request-Id": "no-es-uuid"}
    r = await client.get("/reports/sales", headers=headers)
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["code"] == "INVALID_HEADER"


@pytest.mark.asyncio
async def test_reporte_ventas_correlation_id_invalido(client):
    """X-Correlation-Id con valor no UUID debe retornar 400 con código INVALID_HEADER."""
    headers = {**HEADERS, "X-Correlation-Id": "no-es-uuid"}
    r = await client.get("/reports/sales", headers=headers)
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["code"] == "INVALID_HEADER"


@pytest.mark.asyncio
async def test_recalculo_batch_idempotency_key_invalida(client):
    """Idempotency-Key con valor no UUID debe retornar 400 con código INVALID_HEADER."""
    headers = {**HEADERS, "Idempotency-Key": "no-es-uuid"}
    r = await client.post("/reports/batch/recalculate", headers=headers, json={})
    assert r.status_code == 400
    body = r.json()
    assert body["detail"]["code"] == "INVALID_HEADER"
