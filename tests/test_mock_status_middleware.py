"""
Pruebas de integración para MockStatusMiddleware.

Cubre los escenarios posibles considerando la doble compuerta:
USE_MOCKS=true en el env Y header X-USE-MOCKS: true en la petición.

1. USE_MOCKS=False → el middleware no altera la respuesta.
2. USE_MOCKS=True + sin X-USE-MOCKS → transparente (no-op).
3. USE_MOCKS=True + X-USE-MOCKS: true + header X-MOCK-HTTP-STATUS válido → status forzado.
4. USE_MOCKS=True + X-USE-MOCKS: true + header inválido (no numérico / fuera de rango) → ignorado.
5. USE_MOCKS=True + X-USE-MOCKS: false + header válido → transparente (no-op).
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def client():
    """Cliente HTTP asíncrono apuntando a la aplicación FastAPI en modo test."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ── 1. USE_MOCKS desactivado ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mocks_desactivado_no_altera_status(client):
    """Con USE_MOCKS=False el header X-MOCK-HTTP-STATUS es ignorado aunque X-USE-MOCKS: true esté presente."""
    with patch("app.middleware.mock_status.settings") as mock_settings:
        mock_settings.USE_MOCKS = False
        r = await client.get(
            "/health",
            headers={"X-USE-MOCKS": "true", "X-MOCK-HTTP-STATUS": "503"},
        )
    assert r.status_code == 200


# ── 2. USE_MOCKS activo, sin X-USE-MOCKS ─────────────────────────────────────


@pytest.mark.asyncio
async def test_mocks_activo_sin_header_use_mocks_no_altera_status(client):
    """Con USE_MOCKS=True pero sin X-USE-MOCKS: true el middleware es transparente."""
    with patch("app.middleware.mock_status.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        r = await client.get("/health", headers={"X-MOCK-HTTP-STATUS": "503"})
    assert r.status_code == 200


# ── 3. USE_MOCKS activo + X-USE-MOCKS: true + header válido ──────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("forced_status", [400, 404, 503, 201, 500])
async def test_mocks_activo_fuerza_status(client, forced_status):
    """Con USE_MOCKS=True, X-USE-MOCKS: true y header válido el status code es reemplazado."""
    with patch("app.middleware.mock_status.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        r = await client.get(
            "/health",
            headers={"X-USE-MOCKS": "true", "X-MOCK-HTTP-STATUS": str(forced_status)},
        )
    assert r.status_code == forced_status


# ── 4. USE_MOCKS activo + X-USE-MOCKS: true + header inválido ────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_value", ["abc", "", "99", "600", "0"])
async def test_mocks_activo_header_invalido_ignorado(client, bad_value):
    """Con USE_MOCKS=True, X-USE-MOCKS: true y header no numérico o fuera de rango se ignora."""
    with patch("app.middleware.mock_status.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        r = await client.get(
            "/health",
            headers={"X-USE-MOCKS": "true", "X-MOCK-HTTP-STATUS": bad_value},
        )
    assert r.status_code == 200


# ── 5. USE_MOCKS activo + X-USE-MOCKS: false ─────────────────────────────────


@pytest.mark.asyncio
async def test_mocks_activo_use_mocks_false_no_altera_status(client):
    """Con USE_MOCKS=True pero X-USE-MOCKS: false el middleware es transparente."""
    with patch("app.middleware.mock_status.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        r = await client.get(
            "/health",
            headers={"X-USE-MOCKS": "false", "X-MOCK-HTTP-STATUS": "503"},
        )
    assert r.status_code == 200
