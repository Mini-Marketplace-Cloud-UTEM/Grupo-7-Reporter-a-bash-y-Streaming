# Rol 1 — Agustín: Data & Streaming Engineer

Estado de las tareas del Avance 3 (sugerencias de Fran).

## 1.1 — Handlers con persistencia real ✅

Antes solo `_handle_order_created` escribía en la base; los demás solo logueaban.
Ahora el worker (`app/workers/pubsub_consumer.py`) persiste así:

| Evento | Handler | Tabla destino | Función de servicio |
|---|---|---|---|
| `OrderCreated` | `_handle_order_created` | `fact_sales_summary` | `upsert_sales_from_order` (ya existía) |
| `ShipmentDelivered` | `_handle_shipment_delivered` | `shipment_delivery_log` | `insert_shipment_delivery` (nueva) |
| `InventoryShortage` | `_handle_inventory_shortage` | `inventory_shortage_log` | `insert_inventory_shortage` (nueva) |
| `PaymentApproved` | `_handle_payment_approved` | — (solo log) | deuda técnica: definir métrica |

Se siguió el patrón ORM de Fran: se crearon los modelos `ShipmentDeliveryLog` e
`InventoryShortageLog` en `app/models/analytics.py`, y la nueva migración
`migrations/002_inventory_shortage.sql` para la tabla de quiebres de stock.

**Sobre `delivery_time_minutes`:** el payload de `ShipmentDelivered` no incluye la
fecha del pedido, por lo que el tiempo de entrega se guarda como `NULL` en tiempo real
y se completará en el recálculo batch (cruzando con la fecha de `OrderCreated`), tal
como indicó Fran. El envío igual queda contado en el total de entregas.

**Consistencia (anti-duplicado):** `insert_shipment_delivery` verifica que el
`shipment_id` no exista antes de insertar (la columna es UNIQUE), de modo que un mismo
envío reprocesado por un reintento no se cuenta dos veces.

## 1.2 — Configuración de reintentos y Dead Letter Queue

Estado del código (verificado): los handlers usan
`@retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(5), reraise=True)`.
Al agotar los 5 intentos, la excepción se propaga hasta `_make_callback`, que ejecuta
`message.nack()`; el mensaje vuelve a la cola para reintento posterior. Comportamiento
correcto.

Pendiente (requiere consola de GCP — coordinar con Cristóbal, que tiene el acceso):

- En `Subscriptions > [nombre-sub] > Dead letter topic`, configurar un **DLQ** para que
  los mensajes que fallan repetidamente no se reintenten infinitamente ni se pierdan.
- `Max delivery attempts`: 5 (debe coincidir con `stop_after_attempt(5)`).

Sin DLQ, un mensaje siempre fallido se queda en bucle de `nack`/redelivery. El DLQ lo
deja en una cola aparte para inspección manual.

## 1.3 — Consistencia modelo ORM ↔ schema SQL ✅

Auditoría columna por columna entre `app/models/analytics.py` y las migraciones:

- `fact_sales_summary`: `NUMERIC → Decimal` ✔ · `updated_at` con `server_default=func.now()`
  y `onupdate=func.now()` ✔.
- `agg_top_products`: `last_calculated_at` con `server_default` y `onupdate` ✔.
- `shipment_delivery_log` (modelo nuevo): `shipment_id` UNIQUE ✔ · `delivery_time_minutes`
  nullable ✔ · `recorded_at` con `server_default=func.now()` ✔ — calcado a la migración 001.
- `inventory_shortage_log` (modelo nuevo): calcado a la migración 002 · `occurred_at` con
  `server_default=func.now()` ✔.

Sin discrepancias detectadas.

## Cómo probar (local, con Docker)

1. `docker compose up --build` — levanta Postgres, corre las migraciones (incluida la 002)
   y arranca la API en `localhost:8070`.
2. En otra terminal con `.venv` activo: `python -m scripts.probar_tarea1` — envía un
   evento de envío y uno de quiebre de stock de prueba.
3. En `http://localhost:8070/docs`, probar `GET /reports/delivery-performance`
   (con los 3 headers): `totalDeliveredCount` debe aumentar.

## Coordinación pendiente

- **Grupo 6 (Despacho):** confirmar el esquema de `ShipmentDelivered`; idealmente incluir
  un timestamp de despacho para calcular el tiempo de entrega sin esperar al batch.
- **Fran (tarea 2.3):** `order_status_log` lo lee `GET /reports/orders-by-status`, pero
  aún nadie lo llena. Hay que decidir si `_handle_order_created` inserta también ahí el
  `status` del pedido. Es un cambio en el worker (mi área), coordinado con Fran.
