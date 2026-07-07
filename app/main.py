import logging
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime

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


_DESCRIPTION = """
API de reportería analítica del Mini Marketplace.
Consolida eventos de los servicios upstream (Pedidos, Pagos, Inventario, Despacho)
mediante Google Cloud Pub/Sub y expone métricas agregadas para el BFF (Grupo 1).

---

## Headers obligatorios

Todos los endpoints (excepto `GET /health`) requieren los siguientes headers:

| Header | Tipo | Descripción |
|---|---|---|
| `X-Request-Id` | UUID | Identificador único de la petición |
| `X-Correlation-Id` | UUID | Identificador de trazabilidad entre servicios |
| `X-Consumer` | string | Identificador del consumidor que realiza la petición |
| `Idempotency-Key` | UUID | **Solo en** `POST /reports/batch/recalculate` — previene ejecuciones duplicadas |

---

## Sistema de Mocks

El servicio incluye un mecanismo de mocks de status HTTP diseñado para facilitar
las pruebas de manejo de errores en el BFF (Grupo 1) **sin necesidad de provocar
condiciones reales de fallo** en el backend.

### Activación

El sistema de mocks se controla mediante la variable de entorno `USE_MOCKS`:

```
# .env
USE_MOCKS=true
```

Cuando `USE_MOCKS=false` (valor por defecto), el middleware es completamente
transparente y no modifica ninguna respuesta.

### Uso — header `X-MOCK-HTTP-STATUS`

Con `USE_MOCKS=true`, incluye el header `X-MOCK-HTTP-STATUS` en cualquier
petición con un código HTTP entero entre 100 y 599. El middleware reemplazará
el status code real de la respuesta por el valor indicado.

```
X-MOCK-HTTP-STATUS: 503
```

### Tabla de comportamiento

| `USE_MOCKS` | Header `X-MOCK-HTTP-STATUS` | Resultado |
|---|---|---|
| `false` | cualquier valor | Respuesta real sin modificaciones |
| `true` | ausente | Respuesta real sin modificaciones |
| `true` | valor no entero (ej. `"abc"`) | Respuesta real sin modificaciones (warning en log) |
| `true` | entero fuera de rango (ej. `99`, `600`) | Respuesta real sin modificaciones (warning en log) |
| `true` | entero válido 100–599 (ej. `503`) | Status code de la respuesta reemplazado por `503` |

### Ejemplos con curl

**Simular un 503 Service Unavailable en el reporte de ventas:**
```bash
curl -s -o /dev/null -w "%{http_code}" \\
  https://g7-reporteria-bash-streaming-dev.onrender.com/reports/sales \\
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \\
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \\
  -H "X-Consumer: bff-grupo1" \\
  -H "X-MOCK-HTTP-STATUS: 503"  \\
  -H "X-USE-MOCKS: true"
# Salida: 503
```

**Simular un 429 Too Many Requests en top-products:**
```bash
curl -s -o /dev/null -w "%{http_code}" \\
  "https://g7-reporteria-bash-streaming-dev.onrender.com/reports/top-products?page=1&pageSize=10" \\
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \\
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \\
  -H "X-Consumer: bff-grupo1" \\
  -H "X-MOCK-HTTP-STATUS: 429"  \\
  -H "X-USE-MOCKS: true"
# Salida: 429
```

**Simular un 202 en batch/recalculate (comportamiento real) para verificar idempotencia:**
```bash
curl -s -X POST https://g7-reporteria-bash-streaming-dev.onrender.com/reports/batch/recalculate \\
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \\
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \\
  -H "X-Consumer: bff-grupo1" \\
  -H "Idempotency-Key: 00000000-0000-0000-0000-000000000003" \\
  -H "X-MOCK-HTTP-STATUS: 409" \\
  -H "X-USE-MOCKS: true"
# Simula un conflicto de idempotencia sin necesidad de duplicar la petición real
```

> **Nota:** El mock sobreescribe **únicamente el status code**. El cuerpo de la
> respuesta corresponde siempre al procesamiento real del endpoint.
"""

_OPENAPI_TAGS = [
    {
        "name": "Reportes",
        "description": (
            "Endpoints de reportería analítica. Exponen métricas agregadas calculadas "
            "a partir de los eventos recibidos por Pub/Sub. "
            "Todos los endpoints de este tag admiten el header `X-MOCK-HTTP-STATUS` "
            "cuando `USE_MOCKS=true` está activo en el servidor."
        ),
    },
    {
        "name": "Utilidades",
        "description": "Endpoints de operación y monitoreo del servicio.",
    },
]

app = FastAPI(
    title="Grupo 7 — Reportería, Batch y Streaming",
    version="1.0.0",
    description=_DESCRIPTION,
    openapi_tags=_OPENAPI_TAGS,
    lifespan=lifespan,
)

# ── Middlewares globales ──────────────────────────────────────────────────
# El orden de registro en FastAPI/Starlette es LIFO: el último registrado
# se ejecuta primero.  MockStatusMiddleware va primero en el stack para que
# pueda sobreescribir el status_code después de que toda la cadena procese
# la petición (incluyendo inject_request_id).
app.add_middleware(MockStatusMiddleware)


@app.middleware("http")
async def add_traceability_headers(request: Request, call_next):
    # Generar o capturar UUIDs
    correlation_id = request.headers.get("X-Correlation-Id", str(uuid.uuid4()))
    request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))

    # Log de entrada
    logger.info(
        f"📥 REQUEST IN | Path: {request.url.path} | CorrelationID: {correlation_id} | RequestID: {request_id}"
    )

    request.state.correlation_id = correlation_id
    request.state.request_id = request_id

    response = await call_next(request)

    # Inyectar a la salida
    response.headers["X-Correlation-Id"] = correlation_id
    response.headers["X-Request-Id"] = request_id

    # Log de salida
    logger.info(
        f"📤 RESPONSE OUT | Status: {response.status_code} | CorrelationID: {correlation_id}"
    )

    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    correlation_id = request.headers.get("X-Correlation-Id")
    logger.exception("error_no_manejado ruta=%s", request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "timestamp": datetime.now(UTC).isoformat(),
            "status": 500,
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Ocurrió un error inesperado en el servidor",
            "correlationId": correlation_id,
        },
    )


app.include_router(reports.router)
app.include_router(batch.router)


@app.get("/health", tags=["Utilidades"], summary="Healthcheck del servicio")
async def health():
    return {"status": "ok"}
