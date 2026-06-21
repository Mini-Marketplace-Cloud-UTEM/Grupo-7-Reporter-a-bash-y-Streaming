import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

HEADERS = {
    "X-Request-Id": str(uuid.uuid4()),
    "X-Correlation-Id": str(uuid.uuid4()),
    "X-Consumer": "group-01",
}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_sales_report_missing_headers(client):
    r = await client.get("/reports/sales")
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_sales_report_ok(client):
    mock_report = {
        "period": {"from": None, "to": None},
        "totalSales": 100000,
        "totalOrders": 5,
        "currency": "CLP",
    }
    with patch("app.api.routes.reports.analytics_service.get_sales_report", new_callable=AsyncMock, return_value=mock_report):
        r = await client.get("/reports/sales", headers=HEADERS)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_batch_recalculate_missing_idempotency(client):
    r = await client.post("/reports/batch/recalculate", headers=HEADERS)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_batch_recalculate_ok(client):
    headers = {**HEADERS, "Idempotency-Key": str(uuid.uuid4())}
    with patch("app.api.routes.batch.run_batch_recalculate", new_callable=AsyncMock):
        r = await client.post("/reports/batch/recalculate", headers=headers, json={})
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "QUEUED"
    assert "jobId" in body
