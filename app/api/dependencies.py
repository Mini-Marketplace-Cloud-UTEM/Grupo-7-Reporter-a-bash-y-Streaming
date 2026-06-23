from datetime import UTC, datetime
from uuid import UUID

from fastapi import Header, HTTPException, Request

from app.config import settings


def get_use_mocks(request: Request) -> bool:
    """Retorna True solo si USE_MOCKS=true en el env Y el header X-USE-MOCKS: true está presente."""
    if not settings.USE_MOCKS:
        return False
    return request.headers.get("X-USE-MOCKS", "").lower() == "true"


async def require_headers(
    x_request_id: str = Header(..., alias="X-Request-Id"),
    x_correlation_id: str = Header(..., alias="X-Correlation-Id"),
    x_consumer: str = Header(..., alias="X-Consumer"),
) -> dict:
    """Valida que los tres headers obligatorios estén presentes y sean UUID válidos."""
    for name, value in [("X-Request-Id", x_request_id), ("X-Correlation-Id", x_correlation_id)]:
        try:
            UUID(value)
        except ValueError as err:
            raise HTTPException(
                status_code=400,
                detail={
                    "timestamp": datetime.now(UTC).isoformat(),
                    "status": 400,
                    "code": "INVALID_HEADER",
                    "message": f"El header {name} debe ser un UUID válido",
                    "correlationId": None,
                },
            ) from err
    return {
        "x_request_id": x_request_id,
        "x_correlation_id": x_correlation_id,
        "x_consumer": x_consumer,
    }


async def require_headers_with_idempotency(
    x_request_id: str = Header(..., alias="X-Request-Id"),
    x_correlation_id: str = Header(..., alias="X-Correlation-Id"),
    x_consumer: str = Header(..., alias="X-Consumer"),
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> dict:
    """Valida los tres headers obligatorios más Idempotency-Key para operaciones críticas."""
    for name, value in [
        ("X-Request-Id", x_request_id),
        ("X-Correlation-Id", x_correlation_id),
        ("Idempotency-Key", idempotency_key),
    ]:
        try:
            UUID(value)
        except ValueError as err:
            raise HTTPException(
                status_code=400,
                detail={
                    "timestamp": datetime.now(UTC).isoformat(),
                    "status": 400,
                    "code": "INVALID_HEADER",
                    "message": f"El header {name} debe ser un UUID válido",
                    "correlationId": None,
                },
            ) from err
    return {
        "x_request_id": x_request_id,
        "x_correlation_id": x_correlation_id,
        "x_consumer": x_consumer,
        "idempotency_key": idempotency_key,
    }
