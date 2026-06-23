# Sistema de Mocks — Grupo 7 Reportería, Batch y Streaming

Documentación del mecanismo de mock disponible en el servicio de reportería.
Dirigida a los consumidores del BFF (Grupo 1) y equipos de QA.

---

## Introducción

El servicio expone un sistema de mocks con **doble compuerta**: para que los
mocks se activen deben cumplirse **dos condiciones simultáneamente**:

1. La variable de entorno `USE_MOCKS=true` debe estar configurada en el servidor.
2. La petición HTTP debe incluir el header `X-USE-MOCKS: true`.

Esto permite tener el servidor listo para mocks en entornos de desarrollo/QA
sin que cualquier petición accidentalmente obtenga datos simulados.

El sistema de mocks tiene dos comportamientos:

- **Datos mock**: Los endpoints retornan datos simulados en lugar de consultar
  la base de datos real. Útil para demos y desarrollo sin BD disponible.
- **Mock de status HTTP** (`X-MOCK-HTTP-STATUS`): El middleware reemplaza el
  código de estado de la respuesta por el valor indicado. El cuerpo no se
  modifica. Útil para que el BFF pruebe manejo de errores (reintentos,
  circuit breakers) sin provocar condiciones reales de fallo.

---

## Prerrequisitos

El sistema de mocks está desactivado por defecto. Para habilitarlo:

**1. Configura el servidor** — establece `USE_MOCKS=true` en el archivo `.env`:

```env
USE_MOCKS=true
```

Reinicia el servidor tras el cambio.

**2. Agrega el header en cada petición** — incluye `X-USE-MOCKS: true` en la
petición HTTP que deseas que use mocks.

Si falta cualquiera de las dos condiciones, la petición se procesa con datos
reales de la base de datos.

---

## Header `X-USE-MOCKS`

Este header actúa como interruptor por petición:

```
X-USE-MOCKS: true
```

- `true` (case-insensitive) → activa los mocks para esa petición (si el env también lo permite).
- Cualquier otro valor o ausencia del header → datos reales.

---

## Mock de status HTTP — Header `X-MOCK-HTTP-STATUS`

Con ambas condiciones activas, agrega `X-MOCK-HTTP-STATUS` para forzar el
código de estado HTTP de la respuesta:

```
X-MOCK-HTTP-STATUS: <entero entre 100 y 599>
```

El middleware intercepta la respuesta antes de devolverla al cliente y
reemplaza su `status_code`. El cuerpo siempre refleja el procesamiento real.

---

## Tabla de comportamiento

### Datos mock (contenido de la respuesta)

| `USE_MOCKS` env | Header `X-USE-MOCKS` | Resultado |
|---|---|---|
| `false` | indiferente | Datos reales de la BD |
| `true` | ausente o `false` | Datos reales de la BD |
| `true` | `true` | Datos simulados (mock) |

### Mock de status HTTP (`X-MOCK-HTTP-STATUS`)

| `USE_MOCKS` env | `X-USE-MOCKS` | `X-MOCK-HTTP-STATUS` | Resultado |
|---|---|---|---|
| `false` | indiferente | indiferente | Status real, sin modificación |
| `true` | ausente o `false` | indiferente | Status real, sin modificación |
| `true` | `true` | ausente | Status real, sin modificación |
| `true` | `true` | no es entero (ej. `"abc"`) | Status real; `WARNING` en log |
| `true` | `true` | fuera de rango (ej. `99`, `600`) | Status real; `WARNING` en log |
| `true` | `true` | entero válido 100–599 (ej. `503`) | Status reemplazado por ese valor |

---

## Headers obligatorios (todos los endpoints excepto `/health`)

Independientemente del uso de mocks, todos los endpoints de reportería
requieren los siguientes headers:

| Header | Tipo | Descripción |
|---|---|---|
| `X-Request-Id` | UUID | Identificador único de la petición |
| `X-Correlation-Id` | UUID | Identificador de trazabilidad entre servicios |
| `X-Consumer` | string | Identificador del consumidor |
| `Idempotency-Key` | UUID | Solo en `POST /reports/batch/recalculate` |

---

## Ejemplos `curl` por endpoint

Los ejemplos usan UUIDs fijos para facilitar la reproducción. En entornos
reales, genera UUIDs únicos por petición.

### `GET /reports/sales` — datos mock

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  "http://localhost:8070/reports/sales?from=2024-01-01&to=2024-01-31" \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-USE-MOCKS: true"
```

### `GET /reports/sales` — simular 503 Service Unavailable

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  "http://localhost:8070/reports/sales?from=2024-01-01&to=2024-01-31" \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-USE-MOCKS: true" \
  -H "X-MOCK-HTTP-STATUS: 503"
```

---

### `GET /reports/orders-by-status` — simular 500 Internal Server Error

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  http://localhost:8070/reports/orders-by-status \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-USE-MOCKS: true" \
  -H "X-MOCK-HTTP-STATUS: 500"
```

---

### `GET /reports/top-products` — simular 429 Too Many Requests

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  "http://localhost:8070/reports/top-products?page=1&pageSize=10" \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-USE-MOCKS: true" \
  -H "X-MOCK-HTTP-STATUS: 429"
```

---

### `GET /reports/average-ticket` — simular 404 Not Found

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  http://localhost:8070/reports/average-ticket \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-USE-MOCKS: true" \
  -H "X-MOCK-HTTP-STATUS: 404"
```

---

### `GET /reports/peak-hours` — simular 504 Gateway Timeout

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  http://localhost:8070/reports/peak-hours \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-USE-MOCKS: true" \
  -H "X-MOCK-HTTP-STATUS: 504"
```

---

### `GET /reports/delivery-performance` — simular 503 Service Unavailable

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  http://localhost:8070/reports/delivery-performance \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-USE-MOCKS: true" \
  -H "X-MOCK-HTTP-STATUS: 503"
```

---

### `POST /reports/batch/recalculate` — simular 409 Conflict

```bash
curl -s -w "\nHTTP %{http_code}\n" \
  -X POST http://localhost:8070/reports/batch/recalculate \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "Idempotency-Key: 00000000-0000-0000-0000-000000000003" \
  -H "X-USE-MOCKS: true" \
  -H "X-MOCK-HTTP-STATUS: 409" \
  -d '{"from": "2024-01-01", "to": "2024-01-31"}'
```

---

## Casos de uso recomendados para testing

| Escenario | Status a simular | Endpoint sugerido |
|---|---|---|
| Verificar que el BFF maneja reintentos correctamente | `503` | Cualquier `GET /reports/*` |
| Probar circuit breaker del BFF | `503` repetido | `GET /reports/sales` |
| Validar mensajes de error al usuario final | `500` | `GET /reports/top-products` |
| Probar manejo de rate limiting | `429` | `GET /reports/top-products` |
| Simular sesión expirada / sin autorización | `401` | Cualquier `GET /reports/*` |
| Probar manejo de recurso no encontrado | `404` | `GET /reports/average-ticket` |
| Simular timeout de gateway | `504` | `GET /reports/delivery-performance` |
| Probar idempotencia en batch (conflicto) | `409` | `POST /reports/batch/recalculate` |
| Verificar reintentos en batch fallido | `503` | `POST /reports/batch/recalculate` |

---

## Notas de implementación

- La activación de mocks requiere **dos condiciones simultáneas**: `USE_MOCKS=true`
  en el entorno del servidor Y el header `X-USE-MOCKS: true` en la petición.
  Esto evita que datos simulados lleguen accidentalmente a clientes que no
  lo esperan aunque el servidor esté en modo mock.
- El `MockStatusMiddleware` se aplica como el último middleware en la cadena de
  procesamiento (orden LIFO de Starlette), garantizando que sobreescribe el
  status code definitivo justo antes de devolver la respuesta al cliente.
- El body de la respuesta siempre refleja el procesamiento real (o mock) del
  endpoint. Por ejemplo, al simular un `503` en `GET /reports/sales` con
  `X-USE-MOCKS: true`, la respuesta tendrá `status_code=503` pero el body
  contendrá los datos mock de ventas.
- Esta herramienta está destinada exclusivamente a entornos de desarrollo y
  pruebas. **No debe activarse en producción.**
- El middleware registra eventos `DEBUG` por cada status code reemplazado y
  `WARNING` por cada header inválido o fuera de rango.
