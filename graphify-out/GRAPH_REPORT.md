# Graph Report - .  (2026-07-06)

## Corpus Check
- Corpus is ~34,036 words - fits in a single context window. You may not need a graph.

## Summary
- 610 nodes · 1248 edges · 97 communities (33 shown, 64 thin omitted)
- Extraction: 72% EXTRACTED · 28% INFERRED · 0% AMBIGUOUS · INFERRED: 350 edges (avg confidence: 0.55)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Reports API Layer|Reports API Layer]]
- [[_COMMUNITY_API Dependencies & Validation|API Dependencies & Validation]]
- [[_COMMUNITY_Analytics Service|Analytics Service]]
- [[_COMMUNITY_Alembic Migrations|Alembic Migrations]]
- [[_COMMUNITY_FastAPI App & Middleware|FastAPI App & Middleware]]
- [[_COMMUNITY_Project Docs & CQRS|Project Docs & CQRS]]
- [[_COMMUNITY_Mock Data & Tests|Mock Data & Tests]]
- [[_COMMUNITY_PubSub Event Schemas|Pub/Sub Event Schemas]]
- [[_COMMUNITY_Mock Feature Flag|Mock Feature Flag]]
- [[_COMMUNITY_PubSub Consumer Tests|Pub/Sub Consumer Tests]]
- [[_COMMUNITY_EventEnvelope & Consumer|EventEnvelope & Consumer]]
- [[_COMMUNITY_Consumer Test Fixtures|Consumer Test Fixtures]]
- [[_COMMUNITY_DB Session & Routes|DB Session & Routes]]
- [[_COMMUNITY_App Lifespan & Stop|App Lifespan & Stop]]
- [[_COMMUNITY_Analytics Service Tests|Analytics Service Tests]]
- [[_COMMUNITY_Route Integration Tests|Route Integration Tests]]
- [[_COMMUNITY_REST API Collection|REST API Collection]]
- [[_COMMUNITY_Order Status Logging|Order Status Logging]]
- [[_COMMUNITY_Claude Settings|Claude Settings]]
- [[_COMMUNITY_Batch Recalculate Script|Batch Recalculate Script]]
- [[_COMMUNITY_Inventory Shortage Tests|Inventory Shortage Tests]]
- [[_COMMUNITY_Payment Approved Tests|Payment Approved Tests]]
- [[_COMMUNITY_Claude Local Settings|Claude Local Settings]]
- [[_COMMUNITY_Alembic Async Runner|Alembic Async Runner]]
- [[_COMMUNITY_Git Hook Install|Git Hook Install]]
- [[_COMMUNITY_Git Hooks Scripts|Git Hooks Scripts]]
- [[_COMMUNITY_Test Case 27|Test Case 27]]
- [[_COMMUNITY_Test Case 28|Test Case 28]]
- [[_COMMUNITY_Test Case 29|Test Case 29]]
- [[_COMMUNITY_Test Case 30|Test Case 30]]
- [[_COMMUNITY_Test Case 31|Test Case 31]]
- [[_COMMUNITY_Test Case 32|Test Case 32]]
- [[_COMMUNITY_Test Case 33|Test Case 33]]
- [[_COMMUNITY_Test Case 34|Test Case 34]]
- [[_COMMUNITY_Test Case 35|Test Case 35]]
- [[_COMMUNITY_Test Case 36|Test Case 36]]
- [[_COMMUNITY_Test Case 37|Test Case 37]]
- [[_COMMUNITY_Test Case 38|Test Case 38]]
- [[_COMMUNITY_Test Case 39|Test Case 39]]
- [[_COMMUNITY_Test Case 40|Test Case 40]]
- [[_COMMUNITY_Test Case 41|Test Case 41]]
- [[_COMMUNITY_Test Case 42|Test Case 42]]
- [[_COMMUNITY_Test Case 43|Test Case 43]]
- [[_COMMUNITY_Test Case 44|Test Case 44]]
- [[_COMMUNITY_Test Case 45|Test Case 45]]
- [[_COMMUNITY_Test Case 46|Test Case 46]]
- [[_COMMUNITY_Test Case 47|Test Case 47]]
- [[_COMMUNITY_Test Case 48|Test Case 48]]
- [[_COMMUNITY_Test Case 49|Test Case 49]]
- [[_COMMUNITY_Test Case 50|Test Case 50]]
- [[_COMMUNITY_Test Case 51|Test Case 51]]
- [[_COMMUNITY_Test Case 52|Test Case 52]]
- [[_COMMUNITY_Test Case 53|Test Case 53]]
- [[_COMMUNITY_Test Case 54|Test Case 54]]
- [[_COMMUNITY_Test Case 55|Test Case 55]]
- [[_COMMUNITY_Test Case 56|Test Case 56]]
- [[_COMMUNITY_Test Case 57|Test Case 57]]
- [[_COMMUNITY_Test Case 58|Test Case 58]]
- [[_COMMUNITY_Test Case 59|Test Case 59]]
- [[_COMMUNITY_Test Case 60|Test Case 60]]
- [[_COMMUNITY_Test Case 61|Test Case 61]]
- [[_COMMUNITY_Test Case 62|Test Case 62]]
- [[_COMMUNITY_Test Case 63|Test Case 63]]
- [[_COMMUNITY_Test Case 64|Test Case 64]]
- [[_COMMUNITY_Test Case 65|Test Case 65]]
- [[_COMMUNITY_Test Case 66|Test Case 66]]
- [[_COMMUNITY_Test Case 67|Test Case 67]]
- [[_COMMUNITY_Test Case 68|Test Case 68]]
- [[_COMMUNITY_Test Case 69|Test Case 69]]
- [[_COMMUNITY_Test Case 70|Test Case 70]]
- [[_COMMUNITY_Test Case 71|Test Case 71]]
- [[_COMMUNITY_Test Case 72|Test Case 72]]
- [[_COMMUNITY_Test Case 73|Test Case 73]]
- [[_COMMUNITY_Test Case 74|Test Case 74]]
- [[_COMMUNITY_Test Case 77|Test Case 77]]
- [[_COMMUNITY_Test Case 79|Test Case 79]]
- [[_COMMUNITY_Test Case 80|Test Case 80]]
- [[_COMMUNITY_Test Case 83|Test Case 83]]
- [[_COMMUNITY_Test Case 84|Test Case 84]]
- [[_COMMUNITY_Test Case 85|Test Case 85]]
- [[_COMMUNITY_Test Case 86|Test Case 86]]
- [[_COMMUNITY_Test Case 87|Test Case 87]]
- [[_COMMUNITY_Test Case 88|Test Case 88]]
- [[_COMMUNITY_Test Case 89|Test Case 89]]
- [[_COMMUNITY_Test Case 90|Test Case 90]]
- [[_COMMUNITY_Test Case 91|Test Case 91]]

## God Nodes (most connected - your core abstractions)
1. `datetime` - 41 edges
2. `SalesReport` - 34 edges
3. `OrderStatusCount` - 34 edges
4. `TopProductsResponse` - 34 edges
5. `AverageTicketResponse` - 34 edges
6. `PeakHourItem` - 34 edges
7. `DeliveryPerformanceResponse` - 34 edges
8. `Decimal` - 31 edges
9. `SalesPeriod` - 30 edges
10. `Pagination` - 30 edges

## Surprising Connections (you probably didn't know these)
- `Connection` --uses--> `Base`  [INFERRED]
  alembic/env.py → app/models/analytics.py
- `test_recalculo_batch_ok (idempotency test)` --rationale_for--> `Idempotency Key Pattern for Batch Endpoint`  [INFERRED]
  tests/test_routes.py → docs/avances/avance-3.md
- `test_make_callback (unit tests)` --rationale_for--> `Pub/Sub Ack/Nack Error Handling Strategy`  [INFERRED]
  tests/test_pubsub_consumer.py → docs/avances/avance-3.md
- `test_make_callback_excepcion_llama_nack()` --calls--> `Exception`  [INFERRED]
  tests/test_pubsub_consumer.py → app/main.py
- `str` --uses--> `EventEnvelope`  [INFERRED]
  tests/test_consumer.py → app/schemas/events.py

## Import Cycles
- 1-file cycle: `app/services/analytics_service.py -> app/services/analytics_service.py`
- 1-file cycle: `app/main.py -> app/main.py`
- 1-file cycle: `app/services/batch_service.py -> app/services/batch_service.py`

## Hyperedges (group relationships)
- **FastAPI Request Processing Pipeline** — main_app, mockstatusmiddleware_mockstatusmiddleware, main_inject_request_id, dependencies_require_headers [INFERRED 0.85]
- **Analytics ORM Models backed by SQLAlchemy Base** — analytics_base, analytics_factsalessummary, analytics_aggtopproduct, analytics_batchjob, analytics_orderstatuslog, analytics_shipmentdeliverylog [EXTRACTED 1.00]
- **Batch Recalculate Idempotent Background Flow** — batch_trigger_batch_recalculate, analytics_batchjob, dependencies_require_headers_with_idempotency [EXTRACTED 1.00]
- **Dual ingestion: Pub/Sub real-time and Batch recalculation both write to fact_sales_summary** — pubsub_consumer_handleordercreated, batch_service_runbatchrecalculate, analytics_service_upsertsalesfromorder [INFERRED 0.95]
- **Pub/Sub callback dispatches EventEnvelope to typed event handlers** — pubsub_consumer_makecallback, events_eventenvelope, pubsub_consumer_handleordercreated, pubsub_consumer_handleshipmentdelivered [EXTRACTED 1.00]
- **Mock-enabled analytics service pattern (use_mocks flag bypasses DB)** — analytics_service_getsalesreport, mock_data_salesreport, test_analytics_service_mocks [INFERRED 0.90]
- **Test Suite Covers Full App Layer** — test_dependencies, test_mock_data, test_mock_status_middleware, test_pubsub_consumer, test_routes [EXTRACTED 0.95]
- **Mock System Double Gate: env + header** — double_gate_mock_pattern, test_mock_status_middleware, openapi_mocks_doc [EXTRACTED 0.95]
- **CQRS Write/Read Paths in Reporting Service** — cqrs_pattern, avance4, test_pubsub_consumer [INFERRED 0.75]

## Communities (97 total, 64 thin omitted)

### Community 0 - "Reports API Layer"
Cohesion: 0.12
Nodes (78): date, int, AsyncSession, AverageTicketResponse, bool, date, DeliveryPerformanceResponse, int (+70 more)

### Community 1 - "API Dependencies & Validation"
Cohesion: 0.05
Nodes (68): Valida que los tres headers obligatorios estén presentes y sean UUID válidos., Valida los tres headers obligatorios más Idempotency-Key para operaciones crític, require_headers(), require_headers_with_idempotency(), str, AsyncSession, Configuración centralizada del servicio leída desde variables de entorno o archi, Parámetros de configuración del servicio de Reportería. (+60 more)

### Community 2 - "Analytics Service"
Cohesion: 0.06
Nodes (39): get_average_ticket, get_delivery_performance, get_orders_by_status, get_peak_hours, get_sales_report, get_top_products, log_order_status, log_shipment_delivery (+31 more)

### Community 3 - "Alembic Migrations"
Cohesion: 0.10
Nodes (28): do_run_migrations(), run_async_migrations(), run_migrations_online(), AggTopProduct, Base (DeclarativeBase), BatchJob, FactSalesSummary, OrderStatusLog (+20 more)

### Community 4 - "FastAPI App & Middleware"
Cohesion: 0.08
Nodes (24): global_exception_handler(), inject_request_id(), Request, Request, BaseHTTPMiddleware, Exception, MockStatusMiddleware, Intercepta X-MOCK-HTTP-STATUS y fuerza ese código en la respuesta. (+16 more)

### Community 5 - "Project Docs & CQRS"
Cohesion: 0.09
Nodes (18): Avance 3 — Plan de Acción Operativo, Avance 4 — Integración con Ecosistema, GitHub Actions CI Workflow, CQRS Write/Read Path Separation Pattern, Double Gate Mock Activation Pattern, Idempotency Key Pattern for Batch Endpoint, Sistema de Mocks — Documentación OpenAPI, Pub/Sub Ack/Nack Error Handling Strategy (+10 more)

### Community 6 - "Mock Data & Tests"
Cohesion: 0.08
Nodes (26): average_ticket(), Pruebas unitarias para app/services/mock_data.py.  Verifica que las funciones pu, El ticket promedio debe ser 79647 CLP., Debe retornar exactamente 24 franjas horarias (0-23)., La hora 0 (medianoche) debe tener un conteo de 4 pedidos., El tiempo promedio debe ser 138 minutos y el total de entregas 198., Sin fechas debe retornar el consolidado histórico completo., Con fechas definidas debe retornar el dataset filtrado del período. (+18 more)

### Community 7 - "Pub/Sub Event Schemas"
Cohesion: 0.18
Nodes (18): AbstractEventLoop, str, InventoryShortagePayload, OrderCreatedPayload, PaymentApprovedPayload, Modelos Pydantic para los eventos upstream consumidos desde Google Cloud Pub/Sub, Payload del evento OrderCreated emitido por el Grupo 5 (Pedidos)., Payload del evento PaymentApproved emitido por el Grupo 8 (Pagos). (+10 more)

### Community 8 - "Mock Feature Flag"
Cohesion: 0.15
Nodes (19): get_use_mocks(), Retorna True solo si USE_MOCKS=true en el env Y el header X-USE-MOCKS: true está, bool, Request, _make_request(), MagicMock, str, Pruebas unitarias para app/api/dependencies.py.  Verifica la lógica de get_use_m (+11 more)

### Community 9 - "Pub/Sub Consumer Tests"
Cohesion: 0.12
Nodes (19): _payload_shipment_delivered(), Pruebas unitarias para app/workers/pubsub_consumer.py.  Verifica los handlers de, Un payload sin campos requeridos debe lanzar ValidationError., Cuando el payload incluye status, log_order_status debe recibir ese valor., Un payload sin campos requeridos debe lanzar ValidationError., Un payload vacío debe lanzar excepción de validación., El handler de ShipmentDelivered debe persistir la entrega y loguear el evento., Un payload sin campos requeridos debe lanzar excepción de validación. (+11 more)

### Community 10 - "EventEnvelope & Consumer"
Cohesion: 0.15
Nodes (17): EventEnvelope, Estructura estándar que envuelve todos los eventos del ecosistema., _construir_envelope(), str, Construye un envelope de evento con datos de prueba., El envelope de OrderCreated debe deserializarse con el tipo y orderId correctos., El envelope de PaymentApproved debe deserializarse correctamente., El envelope de InventoryShortage debe deserializarse correctamente. (+9 more)

### Community 11 - "Consumer Test Fixtures"
Cohesion: 0.15
Nodes (16): _construir_mensaje_pubsub(), _payload_order_created(), MagicMock, str, Con un mensaje válido de OrderCreated el callback debe llamar a ack()., Payload mínimo válido para un evento OrderCreated., Con un tipo de evento desconocido el callback debe loguear y llamar a ack() de t, Cuando el future lanza una excepción el callback debe llamar a nack(). (+8 more)

### Community 12 - "DB Session & Routes"
Cohesion: 0.25
Nodes (12): AsyncSession, bool, AsyncSession, get_db(), Configuración de la sesión asíncrona de SQLAlchemy para Supabase Postgres., Dependencia de FastAPI que provee una sesión de base de datos por request., get_average_ticket(), get_delivery_performance() (+4 more)

### Community 13 - "App Lifespan & Stop"
Cohesion: 0.15
Nodes (13): lifespan(), stop_consumers debe llamar a cancel() en cada future de la lista., Con lista vacía no debe lanzar excepción., Con un único future debe cancelarlo correctamente., Con todas las suscripciones configuradas como cadena vacía debe retornar lista v, test_start_consumers_suscripciones_vacias_retorna_lista_vacia(), test_stop_consumers_cancela_todos_los_futures(), test_stop_consumers_lista_vacia() (+5 more)

### Community 14 - "Analytics Service Tests"
Cohesion: 0.25
Nodes (7): Pruebas unitarias para app/services/analytics_service.py.  Verifica la lógica de, Sin pedidos (valores NULL) debe retornar ticket promedio igual a 0., Sin registros en fact_sales_summary debe retornar lista vacía., Sin registro previo para el producto debe crear uno nuevo., test_get_average_ticket_sin_ordenes(), test_get_peak_hours_sin_datos(), test_upsert_top_product_registro_nuevo()

### Community 15 - "Route Integration Tests"
Cohesion: 0.25
Nodes (7): Pruebas de integración para los endpoints de la API de Reportería.  Verifica que, Sin headers obligatorios debe retornar 422., El endpoint de salud debe responder 200 sin headers., Sin headers obligatorios el endpoint debe retornar 422., test_health(), test_orders_by_status_sin_headers(), test_reporte_ventas_sin_headers()

### Community 16 - "REST API Collection"
Cohesion: 0.33
Nodes (5): __export_date, __export_format, __export_source, resources, _type

### Community 17 - "Order Status Logging"
Cohesion: 0.33
Nodes (6): log_order_status(), Registra un cambio de estado de pedido en order_status_log., Debe añadir un OrderStatusLog a la sesión y hacer commit., log_order_status debe crear un nuevo registro en cada llamada.      A diferencia, test_log_order_status_es_log_puro_no_upsert(), test_log_order_status_inserta_registro()

### Community 18 - "Claude Settings"
Cohesion: 0.40
Nodes (4): hooks, PostToolUse, worktree, bgIsolation

### Community 19 - "Batch Recalculate Script"
Cohesion: 0.50
Nodes (4): parse_date(), date, str, Convierte una cadena YYYY-MM-DD a objeto date.

### Community 20 - "Inventory Shortage Tests"
Cohesion: 0.50
Nodes (4): _payload_inventory_shortage(), El handler de InventoryShortage debe emitir un warning con los datos del quiebre, Payload mínimo válido para un evento InventoryShortage., test_handle_inventory_shortage_loguea_warning()

### Community 21 - "Payment Approved Tests"
Cohesion: 0.50
Nodes (4): _payload_payment_approved(), El handler de PaymentApproved solo debe loguear, sin escribir en BD., Payload mínimo válido para un evento PaymentApproved., test_handle_payment_approved_solo_loguea()

## Knowledge Gaps
- **64 isolated node(s):** `bgIsolation`, `PostToolUse`, `allow`, `Request`, `bool` (+59 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **64 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `datetime` connect `API Dependencies & Validation` to `Reports API Layer`, `FastAPI App & Middleware`, `Mock Data & Tests`, `Pub/Sub Event Schemas`, `Pub/Sub Consumer Tests`, `Test Case 42`, `Test Case 43`, `DB Session & Routes`, `Test Case 44`, `Analytics Service Tests`, `Order Status Logging`?**
  _High betweenness centrality (0.268) - this node is a cross-community bridge._
- **Why does `UUID` connect `API Dependencies & Validation` to `Reports API Layer`, `FastAPI App & Middleware`, `Pub/Sub Event Schemas`, `Pub/Sub Consumer Tests`, `Analytics Service Tests`, `Route Integration Tests`?**
  _High betweenness centrality (0.191) - this node is a cross-community bridge._
- **Why does `main()` connect `API Dependencies & Validation` to `Analytics Service`?**
  _High betweenness centrality (0.119) - this node is a cross-community bridge._
- **Are the 21 inferred relationships involving `datetime` (e.g. with `AggTopProduct` and `FactSalesSummary`) actually correct?**
  _`datetime` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `SalesReport` (e.g. with `AsyncSession` and `bool`) actually correct?**
  _`SalesReport` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `OrderStatusCount` (e.g. with `AsyncSession` and `bool`) actually correct?**
  _`OrderStatusCount` has 25 INFERRED edges - model-reasoned connections that need verification._
- **Are the 25 inferred relationships involving `TopProductsResponse` (e.g. with `AsyncSession` and `bool`) actually correct?**
  _`TopProductsResponse` has 25 INFERRED edges - model-reasoned connections that need verification._