<div align="center">

# Grupo 7 — Reporteria, Batch y Streaming

**Servicio de reporteria analitica del Mini Marketplace UTEM.**
Consolida eventos en tiempo real desde Google Cloud Pub/Sub y expone metricas
agregadas para el BFF (Grupo 1).

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-green)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/github/license/Mini-Marketplace-Cloud-UTEM/Grupo-7-Reporter-a-bash-y-Streaming)](LICENSE)

</div>

---

## Descripcion general

Este servicio forma parte del ecosistema **Mini Marketplace Cloud** desarrollado como
proyecto de la asignatura de Cloud Computing en la Universidad Tecnologica Metropolitana
(UTEM). El Grupo 7 es responsable de la capa de reporteria y analisis de datos.

El servicio escucha cuatro topicos de Google Cloud Pub/Sub emitidos por los servicios
upstream (Pedidos, Pagos, Inventario y Despacho) y actualiza en tiempo real dos tablas
analiticas en Supabase Postgres: `fact_sales_summary` y `agg_top_products`. Sobre esas
tablas expone una API REST con metricas de negocio consumidas por el BFF del Grupo 1.

Ademas implementa un mecanismo de **recuperacion batch** que lee los logs de eventos
crudos almacenados en Supabase Storage y recalcula las agregaciones ante cualquier perdida
de mensajes en el canal de streaming.

---

## Caracteristicas

- **Streaming en tiempo real** — Worker asincrono basado en `google-cloud-pubsub` que
  consume cuatro suscripciones simultaneas con reintento exponencial via `tenacity`.
- **Recalculo batch** — Endpoint `POST /reports/batch/recalculate` y script CLI
  independiente para reproesar logs frios desde Supabase Storage.
- **API REST analitica** — Seis endpoints que cubren ventas, pedidos por estado,
  productos mas vendidos, ticket promedio, horas pico y rendimiento de despacho.
- **Trazabilidad distribuida** — Todos los endpoints exigen `X-Request-Id`,
  `X-Correlation-Id` y `X-Consumer` como UUID validos.
- **Documentacion interactiva** — Swagger UI disponible en `/docs` y ReDoc en `/redoc`
  generados automaticamente por FastAPI.
- **Healthcheck** — Endpoint `GET /health` listo para sondas de Docker y Kubernetes.
- **Tests automatizados** — Suite de pruebas con `pytest-asyncio` e `httpx` que cubre
  rutas y validacion de headers.

---

## Stack tecnologico

| Capa | Tecnologia |
|------|-----------|
| Lenguaje | Python 3.11 |
| Framework web | FastAPI 0.111+ |
| Servidor ASGI | Uvicorn (con extras `standard`) |
| ORM asincrono | SQLAlchemy 2.0 (asyncio) + asyncpg |
| Base de datos | Supabase Postgres (PostgreSQL) |
| Almacenamiento de logs | Supabase Storage (bucket `event-logs`) |
| Streaming de eventos | Google Cloud Pub/Sub |
| Validacion de datos | Pydantic v2 + pydantic-settings |
| Cliente HTTP | httpx |
| Reintentos | tenacity |
| Contenedores | Docker + Docker Compose |
| Tests | pytest + pytest-asyncio |

---

## Requisitos previos

Antes de comenzar asegurate de tener instalado:

- **Python** >= 3.11
- **pip** o cualquier gestor de paquetes Python compatible
- **Docker** y **Docker Compose** (para el despliegue en contenedor)
- Una cuenta de **Supabase** con un proyecto activo
- Un proyecto de **Google Cloud** con la API de Pub/Sub habilitada y las suscripciones creadas
- Credenciales de Google Cloud disponibles en el entorno (variable `GOOGLE_APPLICATION_CREDENTIALS`
  o Application Default Credentials configuradas con `gcloud auth application-default login`)

---

## Instalacion y puesta en marcha

### 1. Clonar el repositorio

```bash
git clone git@github.com:Mini-Marketplace-Cloud-UTEM/Grupo-7-Reporter-a-bash-y-Streaming.git
cd Grupo-7-Reporter-a-bash-y-Streaming
```

### 2. Crear y activar el entorno virtual

```bash
python3.11 -m venv .venv
source .venv/bin/activate   # En Windows: .venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
```

Edita `.env` y completa todos los valores:

| Variable | Descripcion | Ejemplo |
|----------|-------------|---------|
| `APP_ENV` | Entorno de ejecucion | `development` |
| `APP_PORT` | Puerto en que escucha el servidor | `8070` |
| `SUPABASE_URL` | URL del proyecto Supabase | `https://xxxx.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | Clave publica de Supabase (antes `anon_key`), para uso en cliente/frontend | `eyJhbGci...` |
| `SUPABASE_SECRET_KEY` | Clave secreta de Supabase (antes `service_role_key`), con privilegios elevados para uso en backend | `eyJhbGci...` |
| `DATABASE_URL` | Cadena de conexion asyncpg a Postgres | `postgresql+asyncpg://user:pass@host:5432/dbname` |
| `GOOGLE_CLOUD_PROJECT` | ID del proyecto de Google Cloud | `mi-proyecto-gcp` |
| `PUBSUB_SUBSCRIPTION_ORDER_CREATED` | Ruta completa de la suscripcion de pedidos creados | `projects/xxx/subscriptions/order-created-sub` |
| `PUBSUB_SUBSCRIPTION_PAYMENT_APPROVED` | Ruta completa de la suscripcion de pagos aprobados | `projects/xxx/subscriptions/payment-approved-sub` |
| `PUBSUB_SUBSCRIPTION_INVENTORY_SHORTAGE` | Ruta completa de la suscripcion de quiebre de inventario | `projects/xxx/subscriptions/inventory-shortage-sub` |
| `PUBSUB_SUBSCRIPTION_SHIPMENT_DELIVERED` | Ruta completa de la suscripcion de envios entregados | `projects/xxx/subscriptions/shipment-delivered-sub` |

### 5. Aplicar el schema de base de datos

Ejecuta el script de migracion inicial en el SQL Editor de Supabase o via `psql`:

```bash
psql "$DATABASE_URL" -f migrations/001_initial_schema.sql
```

Este comando crea las tablas `fact_sales_summary`, `agg_top_products`,
`order_status_log` y `shipment_delivery_log`.

### 6. Levantar en modo desarrollo

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8070 --reload
```

El servidor queda disponible en `http://localhost:8070`.
La documentacion interactiva esta en `http://localhost:8070/docs`.

---

## Despliegue con Docker

### Opcion A — Docker Compose (recomendado)

```bash
docker compose up --build
```

El servicio expone el puerto `8070` y reinicia automaticamente ante fallos.
El healthcheck sondea `GET /health` cada 30 segundos.

### Opcion B — Docker standalone

```bash
docker build -t grupo7-reporteria .
docker run -p 8070:8070 --env-file .env grupo7-reporteria
```

---

## Endpoints de la API

Todos los endpoints requieren los siguientes headers en cada solicitud:

| Header | Tipo | Descripcion |
|--------|------|-------------|
| `X-Request-Id` | UUID | Identificador unico del request |
| `X-Correlation-Id` | UUID | ID de correlacion para trazabilidad distribuida |
| `X-Consumer` | string | Identificador del servicio consumidor (ej: `group-01`) |

### Reportes

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `GET` | `/reports/sales` | Resumen financiero consolidado. Acepta `?from=YYYY-MM-DD&to=YYYY-MM-DD`. Moneda: CLP. |
| `GET` | `/reports/orders-by-status` | Conteo de pedidos agrupados por estado (PENDING, CONFIRMED, DELIVERED, etc.) |
| `GET` | `/reports/top-products` | Ranking paginado de productos por unidades vendidas. Parametros: `page`, `pageSize` (max 100). |
| `GET` | `/reports/average-ticket` | Ticket promedio de compra sobre el historico completo, en CLP. |
| `GET` | `/reports/peak-hours` | Distribucion de pedidos por hora del dia (0–23). |
| `GET` | `/reports/delivery-performance` | Tiempo promedio de entrega en minutos y total de envios completados. |

### Batch

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `POST` | `/reports/batch/recalculate` | Encola un recalculo completo desde los logs de Supabase Storage. Retorna `202 QUEUED`. Requiere header adicional `Idempotency-Key` (UUID). |

### Sistema

| Metodo | Ruta | Descripcion |
|--------|------|-------------|
| `GET` | `/health` | Estado del servicio. |
| `GET` | `/docs` | Documentacion interactiva Swagger UI. |
| `GET` | `/redoc` | Documentacion alternativa ReDoc. |

---

## Proceso batch desde CLI

El script `scripts/batch_recalculate.py` puede ejecutarse de forma independiente,
por ejemplo desde un cron nocturno en GitHub Actions:

```bash
# Recalcular todo el historico
python scripts/batch_recalculate.py

# Recalcular solo un rango de fechas
python scripts/batch_recalculate.py --from 2025-06-01 --to 2025-06-30
```

---

## Esquema de eventos Pub/Sub

El worker consume mensajes que siguen el envelope estandar del Mini Marketplace:

```json
{
  "eventId": "uuid",
  "eventType": "OrderCreated",
  "version": "1.0",
  "occurredAt": "2025-06-01T12:00:00Z",
  "producer": "grupo-05-pedidos",
  "correlationId": "uuid",
  "payload": { ... }
}
```

| `eventType` | Productor | Accion en el worker |
|-------------|-----------|---------------------|
| `OrderCreated` | Grupo 5 (Pedidos) | Acumula monto y conteo en `fact_sales_summary` |
| `PaymentApproved` | Grupo 8 (Pagos) | Registrado en log (sin efecto en metricas aun) |
| `InventoryShortage` | Grupo 4 (Inventario) | Registrado como advertencia en logs estructurados |
| `ShipmentDelivered` | Grupo 6 (Despacho) | Registra tiempo de entrega en `shipment_delivery_log` |

---

## Estructura del proyecto

```
.
├── app/
│   ├── api/
│   │   ├── dependencies.py       # Validacion de headers obligatorios
│   │   └── routes/
│   │       ├── batch.py          # POST /reports/batch/recalculate
│   │       └── reports.py        # GET /reports/*
│   ├── db/
│   │   └── session.py            # Motor asincrono SQLAlchemy + dependencia FastAPI
│   ├── models/
│   │   └── analytics.py          # ORM: FactSalesSummary, AggTopProduct
│   ├── schemas/
│   │   ├── events.py             # Pydantic: EventEnvelope y payloads por tipo
│   │   └── responses.py          # Pydantic: respuestas de cada endpoint
│   ├── services/
│   │   ├── analytics_service.py  # Logica de negocio y upserts en tiempo real
│   │   └── batch_service.py      # Recalculo batch desde Supabase Storage
│   ├── workers/
│   │   └── pubsub_consumer.py    # Consumidor asincrono de Google Cloud Pub/Sub
│   ├── config.py                 # Settings via pydantic-settings (carga .env)
│   └── main.py                   # Instancia FastAPI + lifespan + middlewares
├── migrations/
│   └── 001_initial_schema.sql    # Schema inicial de Supabase Postgres
├── scripts/
│   └── batch_recalculate.py      # Script CLI para recalculo batch standalone
├── tests/
│   ├── test_consumer.py          # Tests del worker Pub/Sub
│   └── test_routes.py            # Tests de endpoints HTTP
├── docs/
│   └── Documento de Arquitectura - Grupo 7 (2).docx
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Ejecucion de tests

```bash
pytest tests/ -v
```

Los tests utilizan `httpx` con transporte ASGI para probar los endpoints sin levantar
un servidor real, y `unittest.mock` para aislar la base de datos.

---

## Contribuir

1. Crear una rama descriptiva desde `main`:
   ```bash
   git checkout -b feat/nombre-de-la-funcionalidad
   ```
2. Realizar los cambios y agregar tests cuando corresponda.
3. Verificar que los tests pasen:
   ```bash
   pytest tests/ -v
   ```
4. Hacer commit con mensajes descriptivos en español o ingles.
5. Abrir un Pull Request hacia `main` describiendo el cambio y su motivacion.

---

## Integrantes — Grupo 7

Proyecto universitario desarrollado para la asignatura de Cloud Computing,
Universidad Tecnologica Metropolitana (UTEM), 2025.

---

<div align="center">
Hecho con dedicacion por el <strong>Grupo 7</strong> — Mini Marketplace Cloud UTEM
</div>
