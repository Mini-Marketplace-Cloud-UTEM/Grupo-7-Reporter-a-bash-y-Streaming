# Avance 4 — Integración con Ecosistema

**Fecha:** 2026-07-06
**Objetivo:** Conectar el servicio de reportería con los grupos del ecosistema (upstream y downstream), demostrar el patrón técnico asignado con evidencia real, y cerrar la trazabilidad distribuida end-to-end.

---

## Resumen del estado actual

Al cierre del Avance 3, el servicio cuenta con:
- Worker Pub/Sub operativo (`app/workers/pubsub_consumer.py`) con los 4 handlers y persistencia en Supabase.
- 6 endpoints analíticos (`/reports/*`) + 1 endpoint batch (`POST /reports/batch/recalculate`) desplegados en Render.
- Headers de validación obligatorios (`X-Request-Id`, `X-Correlation-Id`, `X-Consumer`) en `app/api/dependencies.py`.
- Middleware de trazabilidad que reenvía `X-Request-Id` en la respuesta.
- Mocks funcionales para pruebas con `X-MOCK-HTTP-STATUS`.

Para el E4 el enfoque cambia: de construir a **integrar y demostrar**. Cada entregable requiere evidencia (capturas, videos, colecciones Postman/Bruno, o código ejecutable).

---

## Rol 1 — Bastián Encina: Integración y Comunicación

**Entregable:** Flujo integrado demostrado con capturas o video (mínimo 2 grupos reales).

### 1.1 Integración con Grupo 1 (BFF/Frontend) — downstream

El Grupo 1 consume nuestra API. El contrato que deben cumplir:

| Header | Valor esperado |
|---|---|
| `X-Request-Id` | UUID v4 generado por el BFF en cada request |
| `X-Correlation-Id` | UUID v4 de la sesión/operación |
| `X-Consumer` | Nombre del servicio (ej: `bff-marketplace`) |
| `Idempotency-Key` | UUID v4 solo para `POST /reports/batch/recalculate` |

**Acción concreta:**
1. Contactar al Grupo 1 y enviarles:
   - URL de producción: `https://g7-reporteria-bash-streaming-dev.onrender.com`
   - Documentación OpenAPI: `/docs`
   - Ejemplo de `curl` funcional para al menos 3 endpoints (ver sección al final de este avance).
2. Solicitar que realicen una petición real al servicio y compartir los logs de Render que muestren que el request llegó con los headers correctos.
3. Capturar en Render (Logs) la línea de log con el `X-Correlation-Id` del BFF para tenerlo como evidencia.

**Criterio de éxito:** Logs de Render muestran al menos un request del BFF con sus headers y el servicio retorna `200`.

### 1.2 Integración con grupos upstream (4, 5, 6 u 8) — Pub/Sub

Objetivo: demostrar que al menos **un evento real** emitido por un grupo upstream es recibido y procesado por nuestro worker.

**Acciones concretas:**
1. Contactar al Grupo 5 (Pedidos) para que publiquen un `OrderCreated` de prueba en el tópico GCP.
2. Verificar en Render logs que el worker registra la línea:
   ```
   evento_order_created orderId=<id> correlationId=<uuid>
   ```
3. Consultar el endpoint para confirmar que la métrica cambió:
   ```bash
   curl https://g7-reporteria-bash-streaming-dev.onrender.com/reports/sales \
     -H "X-Request-Id: $(uuidgen)" \
     -H "X-Correlation-Id: $(uuidgen)" \
     -H "X-Consumer: qa-integracion"
   ```
4. Tomar captura del log + respuesta del endpoint. Esa es la evidencia del flujo end-to-end.

**Si Grupo 5 no está disponible**, coordinar con Grupo 6 (ShipmentDelivered) o Grupo 8 (PaymentApproved).

### 1.3 Coordinación de contratos pendientes

Para cada grupo upstream, confirmar por escrito (chat/correo) y guardar en `docs/integracion/`:

| Grupo | Dato a confirmar |
|---|---|
| Grupo 4 (Inventario) | Nombre exacto del tópico Pub/Sub que publican |
| Grupo 5 (Pedidos) | Esquema JSON completo de `OrderCreated` con tipos |
| Grupo 6 (Despacho) | Confirmar que `shipment_id` y `order_id` van en snake_case |
| Grupo 8 (Pagos) | Si `approvedAt` es requerido u opcional en su implementación real |

Crear el directorio `docs/integracion/` y dejar un archivo `contratos.md` con la respuesta de cada grupo.

---

## Rol 2 — Agustín Espinoza: Calidad (QA) y Validaciones

**Entregable:** Colección de pruebas de integración + reporte de resultados (exitosos y fallidos).

### 2.1 Validar contratos reales con Postman o Bruno

Crear una colección con un request por endpoint, cada uno con los headers obligatorios. La colección debe incluir:

**Casos exitosos (esperan `2xx`):**

| Request | Headers adicionales |
|---|---|
| `GET /reports/sales` | `X-Request-Id`, `X-Correlation-Id`, `X-Consumer` |
| `GET /reports/top-products` | ídem |
| `GET /reports/orders-by-status` | ídem |
| `GET /reports/average-ticket` | ídem |
| `GET /reports/peak-hours` | ídem |
| `GET /reports/inventory-shortages` | ídem |
| `POST /reports/batch/recalculate` | + `Idempotency-Key` |

**Casos fallidos (esperan `4xx`):**

| Escenario | Request | Resultado esperado |
|---|---|---|
| Sin `X-Request-Id` | Cualquier endpoint | `422 Unprocessable Entity` |
| Sin `X-Correlation-Id` | Cualquier endpoint | `422 Unprocessable Entity` |
| Sin `X-Consumer` | Cualquier endpoint | `422 Unprocessable Entity` |
| Sin `Idempotency-Key` | `POST /reports/batch/recalculate` | `422 Unprocessable Entity` |
| `X-MOCK-HTTP-STATUS: 503` (con `USE_MOCKS=true` en staging) | Cualquier endpoint | `503 Service Unavailable` |

**Idempotencia del batch:**
1. Hacer `POST /reports/batch/recalculate` con un `Idempotency-Key` fijo (ej: `550e8400-e29b-41d4-a716-446655440000`).
2. Repetir el mismo request con el mismo key.
3. Verificar que ambas respuestas retornan el **mismo `job_id`** y el segundo retorna `200` (no `202`).

### 2.2 Probar casos de error y timeout

Con el servidor en modo mock (`USE_MOCKS=true` en staging o local), probar:

```bash
# Simular 500 Internal Server Error
curl -X GET http://localhost:8070/reports/sales \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -H "X-Consumer: qa-test" \
  -H "X-MOCK-HTTP-STATUS: 500"

# Simular 408 Request Timeout
curl -X GET http://localhost:8070/reports/sales \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -H "X-Consumer: qa-test" \
  -H "X-MOCK-HTTP-STATUS: 408"
```

Documentar la respuesta de cada caso: código HTTP recibido, body de respuesta.

### 2.3 Reporte de pruebas

Crear `docs/avances/reporte-qa-e4.md` con:
1. **Resumen**: N° de tests ejecutados, N° exitosos, N° fallidos.
2. **Tabla de resultados**: endpoint, tipo de caso, resultado esperado, resultado real.
3. **Hallazgos**: si algún endpoint no cumple el contrato esperado, documentarlo con el request exacto y la respuesta recibida.
4. **Estado de contratos upstream**: qué campos de los eventos reales coinciden con los modelos en `app/schemas/events.py` y cuáles difieren.

---

## Rol 3 — Francisco Solís: Desarrollo de Patrones

**Entregable:** Evidencia del patrón técnico implementado (código + demo ejecutable).

### Contexto del patrón asignado

El servicio ya implementa **CQRS (Command Query Responsibility Segregation)**: los workers escritores (`pubsub_consumer.py`) y los lectores de la API (`reports.py`) son caminos completamente separados. El E4 requiere **demostrar y documentar** este patrón explícitamente, y complementarlo con el patrón de **Streaming con Server-Sent Events (SSE)** para reportería en tiempo real.

### 3.1 Implementar endpoint SSE para métricas en tiempo real

Agregar en `app/api/routes/reports.py` un endpoint que emita el resumen de ventas cada N segundos usando SSE:

```python
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio, json

@router.get("/reports/stream/sales", summary="Stream de métricas de ventas en tiempo real")
async def stream_sales(request: Request, db: AsyncSession = Depends(get_db)):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            summary = await get_sales_summary(db)
            yield f"data: {json.dumps(summary)}\n\n"
            await asyncio.sleep(10)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

El helper `get_sales_summary` ya existe en `app/services/analytics_service.py` (es el mismo que usa `GET /reports/sales`). No duplicar lógica: llamar al servicio existente.

Agregar los headers obligatorios via `Depends(require_headers)` igual que el resto de los endpoints.

### 3.2 Documentar el patrón CQRS del servicio

Crear `docs/patrones/cqrs-sse.md` con:

1. **Diagrama de texto** mostrando la separación de comandos y queries:
   ```
   WRITE PATH (Command)
   [Grupos upstream] → [Pub/Sub] → [pubsub_consumer.py] → [Supabase]

   READ PATH (Query)
   [BFF / Cliente] → [GET /reports/*] → [analytics_service.py] → [Supabase]
   [BFF / Cliente] → [GET /reports/stream/sales] → SSE → métricas cada 10s
   ```

2. **Por qué CQRS aquí**: los writes son asíncronos (eventos Pub/Sub) y los reads son síncronos (HTTP). Escalarlos por separado tiene sentido.

3. **Evidencia del SSE**: captura de un cliente conectado al endpoint `/reports/stream/sales` recibiendo eventos (puede ser con `curl -N` o un browser).

### 3.3 Demo ejecutable del patrón

Para la evidencia, conectar al endpoint SSE con curl y capturar la salida:

```bash
# Conectar al stream (en servidor local o producción)
curl -N https://g7-reporteria-bash-streaming-dev.onrender.com/reports/stream/sales \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -H "X-Consumer: demo-patron"
```

La salida debe mostrar líneas `data: {...}` cada 10 segundos. Grabar o capturar 2-3 eventos consecutivos como evidencia.

---

## Rol 4 — Cristóbal: Trazabilidad y Arquitectura

**Entregables:** Capturas de logs con trazabilidad completa + diagrama de arquitectura actualizado.

### 4.1 Completar trazabilidad con `X-Correlation-Id` en logs del worker

Actualmente el worker loguea `correlationId` en cada handler. Verificar que **todos** los handlers incluyan el `correlation_id` en sus líneas de log. Revisar `app/workers/pubsub_consumer.py` handlers:

- `_handle_order_created` → ✅ ya loguea `correlationId`
- `_handle_payment_approved` → verificar que loguea `correlationId`
- `_handle_inventory_shortage` → verificar que loguea `correlationId`
- `_handle_shipment_delivered` → verificar que loguea `correlationId`

Si alguno no lo incluye, agregar el campo al `logger.info(...)` correspondiente. El formato debe ser consistente:

```python
logger.info(
    "evento_<tipo> <campo_clave>=<valor> correlationId=%s",
    ..., correlation_id,
)
```

### 4.2 Verificar que `X-Correlation-Id` se reenvía en respuestas HTTP

El middleware en `app/main.py` debe reenviar `X-Correlation-Id` en la respuesta (se agregó en Avance 3). Confirmar que está presente:

```bash
curl -v https://g7-reporteria-bash-streaming-dev.onrender.com/reports/sales \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: test-correlation-123" \
  -H "X-Consumer: qa"
```

En los headers de respuesta debe aparecer `x-correlation-id: test-correlation-123`. Si no está, revisar el middleware `inject_request_id` en `app/main.py`.

### 4.3 Capturar evidencia de trazabilidad en Render

1. Ir a Render > Logs del servicio.
2. Filtrar por un `correlationId` específico (usar el mismo UUID en el `X-Correlation-Id` de una petición de prueba).
3. Capturar pantalla de los logs mostrando el `correlationId` en:
   - El log del endpoint HTTP (si el BFF consume un endpoint).
   - El log del worker (si llega un evento con ese mismo `correlationId`).

Eso demuestra trazabilidad distribuida: el mismo ID aparece en el BFF → API → worker.

### 4.4 Diagrama de arquitectura actualizado

Actualizar `docs/arquitectura/` (o crear el archivo si no existe) con el diagrama que incluya las integraciones del E4:

```
                    ┌─────────────────────────────────────────┐
                    │          Mini Marketplace Cloud          │
                    └─────────────────────────────────────────┘

  WRITE PATH (eventos asíncronos)
  ┌──────────┐    ┌──────────┐    ┌──────────────────────────┐
  │ Grupo 5  │    │ Grupo 8  │    │  Google Cloud Pub/Sub    │
  │ Pedidos  │───▶│  Pagos   │───▶│  (4 suscripciones)       │
  │ Grupo 4  │    │ Grupo 6  │    └──────────────────────────┘
  │ Inventario│   │ Despacho │                │
  └──────────┘    └──────────┘                ▼
                                    ┌──────────────────────┐
                                    │  Worker Pub/Sub       │
                                    │  pubsub_consumer.py  │
                                    │  + tenacity retry    │
                                    └──────────────────────┘
                                                │
                                                ▼
  READ PATH (API síncrona)          ┌──────────────────────┐
  ┌──────────┐                      │      Supabase         │
  │ Grupo 1  │                      │  fact_sales_summary   │
  │   BFF    │──▶ GET /reports/* ──▶│  agg_top_products     │
  │          │◀─ SSE /stream/sales  │  order_status_log     │
  └──────────┘                      │  shipment_delivery_log│
                                    └──────────────────────┘

  DEPLOYMENT: Render (producción)
  TRAZABILIDAD: X-Request-Id + X-Correlation-Id en todos los requests y logs
```

El diagrama debe estar en un archivo Markdown en `docs/arquitectura/diagrama-e4.md`.

---

## Ejemplos de `curl` para compartir con Grupo 1

```bash
# GET /reports/sales
curl -s https://g7-reporteria-bash-streaming-dev.onrender.com/reports/sales \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -H "X-Consumer: bff-marketplace"

# GET /reports/top-products
curl -s https://g7-reporteria-bash-streaming-dev.onrender.com/reports/top-products \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -H "X-Consumer: bff-marketplace"

# POST /reports/batch/recalculate
curl -s -X POST https://g7-reporteria-bash-streaming-dev.onrender.com/reports/batch/recalculate \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -H "X-Consumer: bff-marketplace" \
  -H "Idempotency-Key: $(uuidgen)"
```

---

## Hitos de Entrega E4

| # | Hito | Responsable | Evidencia requerida |
|---|---|---|---|
| 1 | **Integración real** | Bastián | Log de Render con request del BFF + log de evento upstream procesado |
| 2 | **Contratos validados** | Agustín | Colección Postman/Bruno exportada + `reporte-qa-e4.md` |
| 3 | **Patrón implementado** | Francisco | Endpoint SSE funcional + `docs/patrones/cqrs-sse.md` + captura de stream |
| 4 | **Trazabilidad cerrada** | Cristóbal | Captura de logs con `correlationId` end-to-end + `docs/arquitectura/diagrama-e4.md` |

### Flujo de verificación del E4 completo

```
[Bastián: Grupo 5 publica OrderCreated]
        ↓
[Cristóbal: logs Render muestran correlationId del evento]
        ↓
[Worker procesa → Supabase actualizado]
        ↓
[Francisco: GET /reports/stream/sales emite nueva métrica por SSE]
        ↓
[Agustín: prueba el endpoint y documenta en reporte-qa-e4.md]
```
