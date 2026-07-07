# Patrón CQRS + SSE en el Servicio de Reportería

**Avance 4 — Rol 3 (Francisco Solís)**

---

## 1. CQRS: Separación de comandos y consultas

El servicio implementa **CQRS (Command Query Responsibility Segregation)** de forma natural: el camino de escritura (comandos) y el de lectura (consultas) son completamente independientes, no comparten código ni punto de entrada.

```
WRITE PATH (Command — asíncrono)
┌──────────────┐   evento    ┌─────────────────────┐   upsert   ┌───────────────┐
│  Grupos      │ ──────────▶ │  pubsub_consumer.py  │ ─────────▶ │   Supabase    │
│  4, 5, 6, 8  │  Pub/Sub   │  _handle_order_*     │            │  fact_sales   │
│  (upstream)  │             │  _handle_payment_*   │            │  agg_top_prod │
└──────────────┘             │  _handle_shipment_*  │            │  order_status │
                             │  _handle_inventory_* │            │  shipment_log │
                             └─────────────────────┘            └───────────────┘

READ PATH (Query — síncrono)
┌──────────────┐   HTTP GET   ┌──────────────────────┐   SELECT  ┌───────────────┐
│  Grupo 1     │ ───────────▶ │  routes/reports.py   │ ─────────▶ │   Supabase    │
│  (BFF)       │              │  GET /reports/*      │            │  (solo lectura│
│              │◀─ JSON/SSE ─ │  GET /reports/       │            │   en queries) │
└──────────────┘              │      stream/sales    │            └───────────────┘
                              └──────────────────────┘
```

### Por qué CQRS tiene sentido aquí

| Dimensión | Write path | Read path |
|-----------|-----------|-----------|
| **Trigger** | Evento Pub/Sub (asíncrono) | Request HTTP (síncrono) |
| **Frecuencia** | Baja (pedidos reales) | Alta (dashboards, polling) |
| **Escalado** | Más workers Pub/Sub | Más instancias API |
| **Modelo** | Escribe en tablas de hechos | Lee desde las mismas tablas (pre-agregadas) |
| **Código** | `app/workers/pubsub_consumer.py` | `app/services/analytics_service.py` |

Los writes son asíncronos y event-driven; los reads son síncronos y bajo demanda. Escalarlos por separado es lo correcto: un pico de pedidos no satura la API, y un pico de lecturas no bloquea el worker.

---

## 2. SSE: Streaming de métricas en tiempo real

El endpoint `GET /reports/stream/sales` complementa el patrón CQRS con **Server-Sent Events**: en lugar de que el cliente haga polling, el servidor empuja actualizaciones cada 10 segundos.

### Implementación

```python
# app/api/routes/reports.py
@router.get("/stream/sales")
async def stream_sales(
    request: Request,
    _headers: dict = Depends(require_headers),
    db: AsyncSession = Depends(get_db),
    use_mocks: bool = Depends(get_use_mocks),
):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            summary = await analytics_service.get_sales_report(db, None, None, use_mocks=use_mocks)
            yield f"data: {json.dumps(summary.model_dump())}\n\n"
            await asyncio.sleep(10)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
```

**Decisiones de diseño:**
- **Reutiliza `get_sales_report`** del servicio existente — sin duplicar lógica.
- **Headers obligatorios** vía `Depends(require_headers)` — mismo contrato que el resto de la API.
- **Desconexión limpia** — `request.is_disconnected()` evita que el generador quede colgado si el cliente cierra.
- **`asyncio.sleep(10)`** — yield cooperativo, no bloquea el event loop de FastAPI.

### Flujo con SSE en el sistema completo

```
[Grupo 5 publica OrderCreated]
        │
        ▼ (Pub/Sub)
[Worker acumula ventas en fact_sales_summary]
        │
        ▼ (próximo tick SSE, ≤10s)
[GET /reports/stream/sales emite nueva métrica]
        │
        ▼ (SSE push)
[BFF Grupo 1 recibe evento sin hacer polling]
```

---

## 3. Demo ejecutable

### Conectar al stream (producción)

```bash
curl -N https://g7-reporteria-bash-streaming-dev.onrender.com/reports/stream/sales \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -H "X-Consumer: demo-patron"
```

### Conectar al stream (local)

```bash
# Levantar el servidor
docker compose up -d

curl -N http://localhost:8070/reports/stream/sales \
  -H "X-Request-Id: $(uuidgen)" \
  -H "X-Correlation-Id: $(uuidgen)" \
  -H "X-Consumer: demo-patron"
```

### Salida esperada

Cada 10 segundos el cliente recibe una línea `data:` con el JSON del resumen de ventas:

```
data: {"period": {"from": null, "to": null}, "totalSales": 4820000, "totalOrders": 37, "currency": "CLP"}

data: {"period": {"from": null, "to": null}, "totalSales": 4820000, "totalOrders": 37, "currency": "CLP"}

data: {"period": {"from": null, "to": null}, "totalSales": 5100000, "totalOrders": 39, "currency": "CLP"}
```

El tercer evento muestra `totalSales` y `totalOrders` incrementados porque el worker procesó un nuevo `OrderCreated` entre ticks.

---

## 4. Relación con los entregables del E4

| Hito | Evidencia |
|------|-----------|
| Endpoint SSE funcional | `GET /reports/stream/sales` desplegado en Render |
| CQRS documentado | Este archivo (`docs/patrones/cqrs-sse.md`) |
| Demo ejecutable | Salida de `curl -N` con 2–3 eventos consecutivos |
