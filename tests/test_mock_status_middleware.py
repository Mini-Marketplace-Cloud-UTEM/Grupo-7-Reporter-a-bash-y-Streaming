"""
Pruebas de integración para MockStatusMiddleware.

Cubre los cuatro escenarios posibles:
1. USE_MOCKS=False → el middleware no altera la respuesta.
2. USE_MOCKS=True + header ausente → respuesta inalterada.
3. USE_MOCKS=True + header válido → status forzado.
4. USE_MOCKS=True + header inválido (no numérico / fuera de rango) → ignorado.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import patch

from app.main import app


@pytest_asyncio.fixture
async def client():
    """Cliente HTTP asíncrono apuntando a la aplicación FastAPI en modo test."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── 1. USE_MOCKS desactivado ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mocks_desactivado_no_altera_status(client):
    """Con USE_MOCKS=False el header X-MOCK-HTTP-STATUS es ignorado."""
    with patch("app.middleware.mock_status.settings") as mock_settings:
        mock_settings.USE_MOCKS = False
        r = await client.get("/health", headers={"X-MOCK-HTTP-STATUS": "503"})
    assert r.status_code == 200


# ── 2. USE_MOCKS activo, sin header ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_mocks_activo_sin_header_no_altera_status(client):
    """Con USE_MOCKS=True pero sin el header la respuesta no cambia."""
    with patch("app.middleware.mock_status.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        r = await client.get("/health")
    assert r.status_code == 200


# ── 3. USE_MOCKS activo, header válido ───────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("forced_status", [400, 404, 503, 201, 500])
async def test_mocks_activo_fuerza_status(client, forced_status):
    """Con USE_MOCKS=True y header válido el status code es reemplazado."""
    with patch("app.middleware.mock_status.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        r = await client.get("/health", headers={"X-MOCK-HTTP-STATUS": str(forced_status)})
    assert r.status_code == forced_status


# ── 4. USE_MOCKS activo, header inválido ─────────────────────────────────────

@pytest.mark.asyncio
@pytest.mark.parametrize("bad_value", ["abc", "", "99", "600", "0"])
async def test_mocks_activo_header_invalido_ignorado(client, bad_value):
    """Con USE_MOCKS=True y header no numérico o fuera de rango se ignora."""
    with patch("app.middleware.mock_status.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        r = await client.get(
            "/health",
            headers={"X-MOCK-HTTP-STATUS": bad_value},
        )
    # El endpoint /health devuelve 200; sin mock válido debe mantenerse
    assert r.status_code == 200
