"""
Middleware de mock de status HTTP.

Cuando USE_MOCKS=true, lee el header X-MOCK-HTTP-STATUS de la petición
entrante y sustituye el status code real de la respuesta por el valor
indicado.  Útil para que los consumidores del BFF prueben el manejo de
errores sin necesidad de provocar condiciones reales de fallo.

Comportamiento:
- Si USE_MOCKS es False  → el middleware es transparente (no-op).
- Si USE_MOCKS es True y el header X-MOCK-HTTP-STATUS está ausente o es
  inválido → la respuesta pasa sin modificaciones.
- Si USE_MOCKS es True y el header contiene un entero HTTP válido (100-599)
  → se reemplaza el status_code de la respuesta por ese valor.
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.config import settings

logger = logging.getLogger(__name__)

_MOCK_HEADER = "X-MOCK-HTTP-STATUS"


class MockStatusMiddleware(BaseHTTPMiddleware):
    """Intercepta X-MOCK-HTTP-STATUS y fuerza ese código en la respuesta."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        if not settings.USE_MOCKS:
            return response

        raw = request.headers.get(_MOCK_HEADER)
        if raw is None:
            return response

        try:
            forced_status = int(raw)
        except ValueError:
            logger.warning(
                "mock_status_header_invalido header=%s valor=%r — se ignora",
                _MOCK_HEADER,
                raw,
            )
            return response

        if not (100 <= forced_status <= 599):
            logger.warning(
                "mock_status_fuera_de_rango valor=%d — se ignora",
                forced_status,
            )
            return response

        logger.debug(
            "mock_status_aplicado original=%d forzado=%d ruta=%s",
            response.status_code,
            forced_status,
            request.url.path,
        )
        response.status_code = forced_status
        return response
