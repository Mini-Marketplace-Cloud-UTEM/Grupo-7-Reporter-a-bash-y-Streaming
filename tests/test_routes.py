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
