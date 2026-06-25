# Avance 3 — Plan de Acción Operativo

**Fecha:** 2026-06-25
**Objetivo:** Consolidar el despliegue del servicio de reportería, asegurar la ingesta de datos en tiempo real y validar la integración con el ecosistema de microservicios.

---

## Resumen del estado actual

El servicio FastAPI está operativo con:
- **6 endpoints analíticos** bajo `/reports/*`
- **1 endpoint batch** `POST /reports/batch/recalculate`
- **Worker Pub/Sub** con 4 suscripciones (`OrderCreated`, `PaymentApproved`, `InventoryShortage`, `ShipmentDelivered`)
- **Middleware de mocks** (`X-MOCK-HTTP-STATUS`) y trazabilidad (`X-Request-Id`)
- **4 tablas en Supabase:** `fact_sales_summary`, `agg_top_products`, `order_status_log`, `shipment_delivery_log`

---

## Rol 1 — Agustín: Data & Streaming Engineer

### Contexto técnico

El worker vive en `app/workers/pubsub_consumer.py`. La función `_make_callback` despacha mensajes desde un hilo del cliente Pub/Sub hacia el event loop de asyncio usando `run_coroutine_threadsafe`. Los handlers individuales (`_handle_order_created`, etc.) ya tienen `@retry` de `tenacity` con backoff exponencial (min=2s, max=30s, 5 intentos).

### Tareas

#### 1.1 Completar handlers con lógica de persistencia real

Actualmente solo `_handle_order_created` escribe en la base de datos. Los otros tres handlers solo loguean. Hay que conectarlos a las tablas auxiliares.

**`_handle_inventory_shortage` → tabla `order_status_log` o nueva tabla:**

El esquema en `migrations/001_initial_schema.sql` no tiene tabla para quiebres de stock. Opciones:
- Agregar una tabla `inventory_shortage_log` en una nueva migración.
- Alternativamente, reutilizar `order_status_log` con `status = 'SHORTAGE'` si el BFF no necesita detalle de producto.

Migración sugerida (`migrations/002_inventory_shortage.sql`):
```sql
CREATE TABLE IF NOT EXISTS inventory_shortage_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id VARCHAR NOT NULL,
  current_stock INTEGER NOT NULL,
  requested_quantity INTEGER NOT NULL,
  occurred_at TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_shortage_product ON inventory_shortage_log (product_id);
```

**`_handle_shipment_delivered` → tabla `shipment_delivery_log`:**

La tabla ya existe. El handler debe calcular `delivery_time_minutes` desde la fecha del pedido hasta `delivered_at`. Si no se tiene la fecha del pedido en el payload, usar `NULL` y completar en el recálculo batch.

Implementación mínima en `pubsub_consumer.py`:
```python
from app.models.analytics import ShipmentDeliveryLog  # modelo a crear

async def _handle_shipment_delivered(payload: dict, correlation_id: str) -> None:
    data = ShipmentDeliveredPayload(**payload)
    async with AsyncSessionLocal() as db:
        record = ShipmentDeliveryLog(
            shipment_id=data.shipment_id,
            order_id=data.order_id,
            delivered_at=data.delivered_at,
            city=data.city,
        )
        db.add(record)
        await db.commit()
    logger.info(
        "evento_shipment_delivered envioId=%s pedidoId=%s ciudad=%s correlationId=%s",
        data.shipment_id, data.order_id, data.city, correlation_id,
    )
```

El modelo ORM `ShipmentDeliveryLog` debe agregarse en `app/models/analytics.py` siguiendo el patrón de `FactSalesSummary`.

#### 1.2 Validar configuración de reintentos

El comportamiento actual de `@retry` con `reraise=True` hace que, al agotar los 5 intentos, la excepción se propague hasta `_make_callback`, que llama `message.nack()`. Verificar que el tópico Pub/Sub tenga una **Dead Letter Queue (DLQ)** configurada en GCP para evitar pérdida permanente de mensajes tras los reintentos.

Checklist en consola GCP:
- `Subscriptions > [nombre-sub] > Dead letter topic` — debe estar configurado.
- `Max delivery attempts` — recomendado: 5 (coincide con `stop_after_attempt(5)`).

#### 1.3 Validar consistencia del modelo ORM con el schema SQL

Comparar los campos de `app/models/analytics.py` contra `migrations/001_initial_schema.sql` columna por columna. Prestar atención a:
- Tipos: `NUMERIC` en SQL → `Decimal` en Python (ya correcto en `upsert_sales_from_order`).
- `updated_at` en `FactSalesSummary`: el modelo ORM debe tener `server_default=func.now()` y `onupdate=func.now()`.
- `last_calculated_at` en `AggTopProduct`: ídem.

---

## Rol 2 — Fran: API & Batch Developer

### Contexto técnico

Los 6 endpoints están en `app/api/routes/reports.py` y el batch en `app/api/routes/batch.py`. La lógica de negocio vive en `app/services/analytics_service.py` y `app/services/batch_service.py`. Los headers obligatorios se validan en `app/api/dependencies.py`.

### Tareas

#### 2.1 Revisar y completar `app/api/dependencies.py`

Confirmar que `require_headers` valida los tres headers obligatorios:
- `X-Request-Id` (UUID)
- `X-Correlation-Id` (UUID)
- `X-Consumer` (string no vacío)

Y que `require_headers_with_idempotency` agrega:
- `Idempotency-Key` (UUID)

Si algún header falta, la dependencia debe retornar `422 Unprocessable Entity` con un mensaje claro, **no** `400`. FastAPI usa 422 para errores de validación por convención.

#### 2.2 Implementar lógica de idempotencia real en batch

El endpoint `POST /reports/batch/recalculate` actualmente genera un `job_id` nuevo en cada llamada. Para prevenir ejecuciones duplicadas con el mismo `Idempotency-Key`, se necesita un registro de jobs.

Migración sugerida (`migrations/003_batch_jobs.sql`):
```sql
CREATE TABLE IF NOT EXISTS batch_jobs (
  idempotency_key UUID PRIMARY KEY,
  job_id UUID NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'QUEUED',
  created_at TIMESTAMP NOT NULL DEFAULT now(),
  completed_at TIMESTAMP
);
```

Flujo en `app/api/routes/batch.py`:
1. Leer `Idempotency-Key` del header.
2. Consultar `batch_jobs` por `idempotency_key`.
3. Si existe → retornar `200` con el `job_id` original y `status` actual (sin re-encolar).
4. Si no existe → insertar en `batch_jobs`, encolar el background task, retornar `202`.

#### 2.3 Completar endpoint `GET /reports/orders-by-status`

El servicio `get_orders_by_status` lee de `order_status_log`, pero el worker de Pub/Sub actualmente no inserta en esa tabla (el handler `_handle_order_created` solo actualiza `fact_sales_summary`). Coordinar con Agustín para que el handler también inserte en `order_status_log` con `status = payload.status` cuando el campo esté presente.

#### 2.4 Script CLI de recálculo batch

El script `scripts/batch_recalculate.py` debe poder ejecutarse fuera de la API:

```bash
# Uso esperado
python scripts/batch_recalculate.py --from 2026-06-01 --to 2026-06-25
python scripts/batch_recalculate.py  # sin rango → recalcula todo el histórico
```

Verificar que el script:
- Inicialice `AsyncSessionLocal` correctamente (no depender de la instancia del endpoint).
- Use `asyncio.run()` como punto de entrada.
- Imprima el `job_id` y la cantidad de eventos procesados al terminar.

#### 2.5 Añadir middleware de trazabilidad de `X-Correlation-Id` en respuestas

El middleware actual (`inject_request_id` en `app/main.py`) solo reenvía `X-Request-Id` en la respuesta. Agregar también `X-Correlation-Id` para que el BFF pueda trazar la petición end-to-end:

```python
@app.middleware("http")
async def inject_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    correlation_id = request.headers.get("X-Correlation-Id", "")
    response = await call_next(request)
    response.headers["X-Request-Id"] = request_id
    if correlation_id:
        response.headers["X-Correlation-Id"] = correlation_id
    return response
```

---

## Rol 3 — Cristóbal: Cloud & DevOps Engineer

### Contexto técnico

El servicio se despliega en Railway. El `Dockerfile` y `docker-compose.yml` están en la raíz. Las variables de entorno se declaran en `.env.example`.

### Tareas

#### 3.1 Configurar variables de entorno en Railway (producción)

Las siguientes variables deben estar configuradas en el panel de Railway (no en el repositorio):

| Variable | Descripción |
|---|---|
| `APP_ENV` | `production` |
| `APP_PORT` | `8070` |
| `SUPABASE_URL` | URL del proyecto Supabase |
| `SUPABASE_ANON_KEY` | Clave anónima de Supabase |
| `DATABASE_URL` | `postgresql+asyncpg://...` (connection string de Supabase) |
| `GOOGLE_CLOUD_PROJECT` | ID del proyecto GCP |
| `PUBSUB_SUBSCRIPTION_ORDER_CREATED` | `projects/.../subscriptions/order-created-sub` |
| `PUBSUB_SUBSCRIPTION_PAYMENT_APPROVED` | `projects/.../subscriptions/payment-approved-sub` |
| `PUBSUB_SUBSCRIPTION_INVENTORY_SHORTAGE` | `projects/.../subscriptions/inventory-shortage-sub` |
| `PUBSUB_SUBSCRIPTION_SHIPMENT_DELIVERED` | `projects/.../subscriptions/shipment-delivered-sub` |
| `USE_MOCKS` | `false` en producción, `true` en staging |

La variable `GOOGLE_APPLICATION_CREDENTIALS` debe apuntar al archivo de service account JSON montado en el contenedor, o configurar Workload Identity en GCP para evitar archivos de credenciales.

#### 3.2 Verificar healthcheck en Railway

Railway detecta el healthcheck automáticamente si el servicio responde `200` en `GET /health`. Confirmar que el `Dockerfile` expone el puerto correcto:

```dockerfile
EXPOSE 8070
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8070"]
```

En Railway, configurar:
- **Health check path:** `/health`
- **Health check timeout:** `30s`
- **Restart policy:** `on-failure`

#### 3.3 Pipeline CI/CD en GitHub Actions

Verificar que el workflow de CI ejecute en orden:
1. `ruff check` (linting)
2. `ruff format --check` (formato)
3. `pytest` con cobertura

El paso de despliegue a Railway debe ejecutarse **solo en push a `main`** y **solo si CI pasa**.

Plantilla de job de despliegue (`.github/workflows/deploy.yml`):
```yaml
deploy:
  needs: [lint, test]
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main'
  steps:
    - uses: actions/checkout@v4
    - name: Deploy to Railway
      run: npx @railway/cli@latest up --service grupo-7-reporteria
      env:
        RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

#### 3.4 Ejecutar migraciones pendientes en Supabase

Antes del siguiente despliegue, aplicar las migraciones en orden desde el SQL Editor de Supabase:
1. `migrations/001_initial_schema.sql` (si no está aplicada)
2. `migrations/002_inventory_shortage.sql` (nueva — ver Rol de Agustín)
3. `migrations/003_batch_jobs.sql` (nueva — ver Rol de Fran)

Confirmar la existencia de las tablas con:
```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
```

#### 3.5 Configurar Docker Compose para desarrollo local

El `docker-compose.yml` debe permitir levantar el servicio localmente sin Railway. Verificar que:
- El servicio `postgres` esté configurado con las variables de `POSTGRES_*` del `.env.example`.
- La variable `DATABASE_URL` use `postgres` como hostname (nombre del servicio en Compose), no `localhost`.
- Exista un servicio `pubsub-emulator` o instrucciones claras para emular Pub/Sub localmente usando la variable de entorno `PUBSUB_EMULATOR_HOST`.

---

## Rol 4 — Bastián Encina: QA & Core Documentation

### Contexto técnico

Los tests están en `tests/`. Usan `pytest-asyncio` e `httpx`. Los archivos actuales cubren: rutas (`test_routes.py`), servicio de analytics (`test_analytics_service.py`), worker Pub/Sub (`test_pubsub_consumer.py`), batch (`test_batch_service.py`), middleware de mocks (`test_mock_status_middleware.py`), y datos mock (`test_mock_data.py`).

### Tareas

#### 4.1 Ejecutar la suite completa y reportar cobertura

```bash
# Desde la raíz del proyecto
pytest --cov=app --cov-report=term-missing --cov-report=html -v
```

El reporte HTML se genera en `htmlcov/index.html`. El objetivo es **≥ 80% de cobertura en `app/`**.

Prestar atención a módulos con cobertura baja:
- `app/services/batch_service.py` — la integración con Supabase Storage es difícil de testear; usar mocks de `supabase.create_client`.
- `app/workers/pubsub_consumer.py` — mockear el cliente `pubsub_v1.SubscriberClient`.

#### 4.2 Validar contrato de API con Grupo 1 (BFF)

Solicitar al Grupo 1 el esquema de requests que enviarán. Verificar punto a punto:

| Endpoint nuestro | Header requerido | ¿Grupo 1 lo envía? |
|---|---|---|
| Todos | `X-Request-Id` | Confirmar |
| Todos | `X-Correlation-Id` | Confirmar |
| Todos | `X-Consumer` | Confirmar |
| `POST /reports/batch/recalculate` | `Idempotency-Key` | Confirmar |

Enviarles la URL de documentación OpenAPI del servicio en producción:
```
https://grupo-7-reporter-a-bash-y-streaming-production.up.railway.app/docs
```

Incluir en el correo/mensaje:
- Ejemplo de `curl` funcional para cada endpoint (ya documentados en `app/main.py`).
- Instrucciones del sistema de mocks (`X-MOCK-HTTP-STATUS` + `USE_MOCKS=true`).

#### 4.3 Validar contratos con grupos upstream (4, 5, 6, 8)

Para cada grupo, confirmar el esquema JSON exacto que publican en Pub/Sub. Compararlo contra los modelos Pydantic en `app/schemas/events.py`:

| Grupo | Evento | Modelo en nuestro código | Campo crítico a confirmar |
|---|---|---|---|
| Grupo 5 (Pedidos) | `OrderCreated` | `OrderCreatedPayload` | `totalAmount` como número, `createdAt` en ISO 8601 |
| Grupo 8 (Pagos) | `PaymentApproved` | `PaymentApprovedPayload` | `amountPaid` como número, `approvedAt` opcional |
| Grupo 4 (Inventario) | `InventoryShortage` | `InventoryShortagePayload` | `currentStock` y `requestedQuantity` como enteros |
| Grupo 6 (Despacho) | `ShipmentDelivered` | `ShipmentDeliveredPayload` | `shipment_id` y `order_id` en snake_case (confirmar convención) |

El `EventEnvelope` espera siempre: `eventId`, `eventType`, `version`, `occurredAt`, `producer`, `correlationId`, `payload`.

Pedir a los grupos upstream que publiquen un evento de prueba en el tópico y verificar que el worker lo procese sin errores revisando los logs en Railway.

#### 4.4 Completar README final

El `README.md` debe incluir:
1. **Descripción del servicio** — qué hace y qué problema resuelve.
2. **Arquitectura** — diagrama de texto mostrando los grupos upstream → Pub/Sub → Worker → Supabase → API → BFF.
3. **Setup local** — pasos con `docker-compose up` o `uvicorn` directo.
4. **Variables de entorno** — tabla con descripción de cada variable en `.env.example`.
5. **Endpoints** — tabla con método, ruta, headers requeridos y descripción breve.
6. **Sistema de mocks** — cómo activarlo y usarlo (ya documentado en `app/main.py`, trasladar al README).
7. **Ejecutar tests** — comando `pytest` con flags de cobertura.
8. **Despliegue** — URL de producción en Railway.

---

## 5. Plan de Coordinación Externa

### Con Grupo 1 (BFF/Frontend) — Bastián coordina

**Acción inmediata:** Enviar enlace a `/docs` de producción junto con este mensaje:

> "Para consumir nuestra API necesitan incluir siempre los headers `X-Request-Id` (UUID), `X-Correlation-Id` (UUID) y `X-Consumer` (string). Sin ellos recibirán 422. Para pruebas de error usen el header `X-MOCK-HTTP-STATUS: 503` (o cualquier código 100–599) — funciona solo cuando nuestro servidor tiene `USE_MOCKS=true`."

**Acción de seguimiento:** Pedir que nos compartan una petición de prueba para verificar que los headers llegan correctamente.

### Con Grupos Upstream (4, 5, 6, 8) — Bastián coordina

Para cada grupo, confirmar por escrito:

1. **Nombre del tópico Pub/Sub** que publican (para que Cristóbal configure las suscripciones).
2. **Esquema JSON completo** de su evento (comparar contra `app/schemas/events.py`).
3. **Formato de fechas** — debe ser ISO 8601 con timezone (`2026-06-25T14:30:00Z`).
4. **Ruta del log en Supabase Storage** — el bucket `event-logs` y el formato de nombre de archivo que usan, para que el recálculo batch pueda leerlos.

---

## 6. Hitos de Entrega

| # | Hito | Responsable | Criterio de éxito |
|---|---|---|---|
| 1 | **Estabilización** | Agustín + Cristóbal | Worker recibe y persiste eventos reales sin errores en staging durante 30 minutos |
| 2 | **Validación** | Bastián + todos | `pytest` verde al 100%; cobertura ≥ 80% en `app/` |
| 3 | **Integración** | Fran + Bastián | Flujo completo verificado: evento emitido por grupo upstream → worker lo procesa → endpoint API retorna la métrica actualizada |

### Flujo de verificación del Hito 3

```
[Grupo 5 publica OrderCreated en Pub/Sub]
        ↓
[Worker _handle_order_created recibe el mensaje]
        ↓
[upsert_sales_from_order actualiza fact_sales_summary]
        ↓
[GET /reports/sales retorna totalOrders incrementado en 1]
        ↓
[GET /reports/average-ticket retorna nuevo promedio]
```

Comando de verificación manual:

```bash
# 1. Consultar ventas antes del evento
curl -s https://grupo-7-reporter-a-bash-y-streaming-production.up.railway.app/reports/sales \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -H "X-Consumer: qa-verificacion"

# 2. Pedir al Grupo 5 que publique un OrderCreated de prueba

# 3. Esperar ~5 segundos y consultar nuevamente
# El totalOrders debe haber aumentado en 1
```

---

## 7. Deuda técnica identificada

Los siguientes puntos no son bloqueantes para el hito actual pero deben documentarse para la siguiente iteración:

- `_handle_payment_approved` no persiste datos (solo loguea). Definir si `PaymentApproved` debe afectar alguna métrica.
- El recálculo batch no tiene endpoint de consulta de estado (`GET /reports/batch/jobs/{job_id}`). El BFF no puede saber si terminó.
- No hay paginación en `GET /reports/orders-by-status` ni en `GET /reports/peak-hours`.
- El `timeout=30` en `future.result()` dentro del callback de Pub/Sub puede bloquear el hilo del cliente si la base de datos tarda. Evaluar reducirlo o hacerlo configurable.
