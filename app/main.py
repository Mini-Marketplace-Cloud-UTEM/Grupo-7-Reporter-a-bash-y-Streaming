import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.routes import batch, reports
from app.middleware.mock_status import MockStatusMiddleware
from app.workers.pubsub_consumer import start_consumers, stop_consumers

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)

_pubsub_futures: list = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _pubsub_futures
    try:
        _pubsub_futures = await start_consumers()
        logger.info("consumidores_pubsub_iniciados cantidad=%d", len(_pubsub_futures))
    except Exception:
        logger.exception("pubsub_inicio_fallido — servicio funcionando sin consumidor de streaming")
    yield
    await stop_consumers(_pubsub_futures)
    logger.info("consumidores_pubsub_detenidos")


app = FastAPI(
    title="Grupo 7 — Reportería, Batch y Streaming",
    version="1.0.0",
    description=(
        "API de reportería analítica del Mini Marketplace. "
        "Consolida eventos de los servicios upstream (Pedidos, Pagos, Inventario, Despacho) "
        "mediante Google Cloud Pub/Sub y expone métricas agregadas para el BFF (Grupo 1)."
    ),
    lifespan=lifespan,
)

# ── Middlewares globales ──────────────────────────────────────────────────
# El orden de registro en FastAPI/Starlette es LIFO: el último registrado
# se ejecuta primero.  MockStatusMiddleware va primero en el stack para que
# pueda sobreescribir el status_code después de que toda la cadena procese
# la petición (incluyendo inject_request_id).
app.add_middleware(MockStatusMiddleware)


@app.middleware("http")
async def inject_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = request.headers.get("X-Correlation-Id")
    logger.exception("error_no_manejado ruta=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": 500,
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Ocurrió un error inesperado en el servidor",
            "correlationId": correlation_id,
        },
    )


app.include_router(reports.router)
app.include_router(batch.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
