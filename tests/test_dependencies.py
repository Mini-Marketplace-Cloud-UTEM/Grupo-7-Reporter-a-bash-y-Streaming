"""
Pruebas unitarias para app/api/dependencies.py.

Verifica la lógica de get_use_mocks según el valor de settings.USE_MOCKS
y el header X-USE-MOCKS enviado en el request.
"""

from unittest.mock import MagicMock, patch

from app.api.dependencies import get_use_mocks


def _make_request(header_value: str | None = None) -> MagicMock:
    """Construye un mock de Request con los headers indicados."""
    request = MagicMock()
    headers = {}
    if header_value is not None:
        headers["X-USE-MOCKS"] = header_value
    request.headers = headers
    return request


# ---------------------------------------------------------------------------
# USE_MOCKS=False en settings
# ---------------------------------------------------------------------------


def test_get_use_mocks_settings_false_sin_header():
    """Cuando USE_MOCKS=False en settings debe retornar False aunque no haya header."""
    request = _make_request()
    with patch("app.api.dependencies.settings") as mock_settings:
        mock_settings.USE_MOCKS = False
        result = get_use_mocks(request)
    assert result is False


def test_get_use_mocks_settings_false_con_header_true():
    """Cuando USE_MOCKS=False en settings debe retornar False aunque el header sea 'true'."""
    request = _make_request("true")
    with patch("app.api.dependencies.settings") as mock_settings:
        mock_settings.USE_MOCKS = False
        result = get_use_mocks(request)
    assert result is False


# ---------------------------------------------------------------------------
# USE_MOCKS=True en settings
# ---------------------------------------------------------------------------


def test_get_use_mocks_settings_true_header_true():
    """Cuando USE_MOCKS=True en settings y el header es 'true' debe retornar True."""
    request = _make_request("true")
    with patch("app.api.dependencies.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        result = get_use_mocks(request)
    assert result is True


def test_get_use_mocks_settings_true_header_false():
    """Cuando USE_MOCKS=True en settings pero el header es 'false' debe retornar False."""
    request = _make_request("false")
    with patch("app.api.dependencies.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        result = get_use_mocks(request)
    assert result is False


def test_get_use_mocks_settings_true_sin_header():
    """Cuando USE_MOCKS=True pero el header X-USE-MOCKS no está presente debe retornar False."""
    request = _make_request()
    with patch("app.api.dependencies.settings") as mock_settings:
        mock_settings.USE_MOCKS = True
        result = get_use_mocks(request)
    assert result is False
