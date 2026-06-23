# Sistema de Mocks — Grupo 7 Reportería, Batch y Streaming

Documentación del mecanismo de mock de status HTTP disponible en el servicio de reportería.
Dirigida a los consumidores del BFF (Grupo 1) y equipos de QA.

---

## Introducción

El servicio expone un middleware opcional (`MockStatusMiddleware`) que permite a los
consumidores forzar el código de estado HTTP de cualquier respuesta enviando un header
especial. El objetivo es que el BFF y los equipos de integración puedan probar el
manejo de errores (reintentos, circuit breakers, mensajes de error al usuario) sin
necesidad de provocar condiciones reales de fallo en el backend ni en la base de datos.

El cuerpo de la respuesta **no se modifica**: el servidor procesa la petición
normalmente y solo se sobreescribe el `status_code` final.

---

## Prerrequisitos

El sistema de mocks está desactivado por defecto. Para habilitarlo, establece la
variable de entorno `USE_MOCKS=true` en el archivo `.env` del servidor:

```env
USE_MOCKS=true
```

Reinicia el servidor tras el cambio. Mientras `USE_MOCKS=false`, el middleware es
completamente transparente y no tiene ningún efecto sobre las respuestas.

---

## Cómo usar el header `X-MOCK-HTTP-STATUS`

Con el servidor corriendo con `USE_MOCKS=true`, agrega el header `X-MOCK-HTTP-STATUS`
a cualquier petición con el código HTTP que quieras forzar:

```
X-MOCK-HTTP-STATUS: <entero entre 100 y 599>
```

El middleware intercepta la respuesta antes de devolverla al cliente y reemplaza
su status code por el valor indicado.

---

## Tabla de comportamiento del middleware

| `USE_MOCKS` | Header `X-MOCK-HTTP-STATUS` presente | Valor del header | Resultado |
|---|---|---|---|
| `false` | indiferente | indiferente | Respuesta real, sin modificaciones |
| `true` | no | — | Respuesta real, sin modificaciones |
| `true` | sí | no es un entero (ej. `"abc"`) | Respuesta real, sin modificaciones; se registra `WARNING` en log |
| `true` | sí | entero fuera de rango (ej. `99`, `600`) | Respuesta real, sin modificaciones; se registra `WARNING` en log |
| `true` | sí | entero válido 100–599 (ej. `503`) | Status code reemplazado por el valor indicado |

---

## Headers obligatorios (todos los endpoints excepto `/health`)

Recuerda que independientemente del uso de mocks, todos los endpoints de reportería
requieren los siguientes headers:

| Header | Tipo | Descripción |
|---|---|---|
| `X-Request-Id` | UUID | Identificador único de la petición |
| `X-Correlation-Id` | UUID | Identificador de trazabilidad entre servicios |
| `X-Consumer` | string | Identificador del consumidor |
| `Idempotency-Key` | UUID | Solo en `POST /reports/batch/recalculate` |

---

## Ejemplos `curl` por endpoint

Los ejemplos usan UUIDs fijos para facilitar la reproducción. En entornos reales,
genera UUIDs únicos por petición.

### `GET /reports/sales`

**Simular 503 Service Unavailable:**
```bash
curl -s -w "\nHTTP %{http_code}\n" \
  "http://localhost:8070/reports/sales?from=2024-01-01&to=2024-01-31" \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-MOCK-HTTP-STATUS: 503"
```

**Simular 401 Unauthorized:**
```bash
curl -s -w "\nHTTP %{http_code}\n" \
  "http://localhost:8070/reports/sales" \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-MOCK-HTTP-STATUS: 401"
```

---

### `GET /reports/orders-by-status`

**Simular 500 Internal Server Error:**
```bash
curl -s -w "\nHTTP %{http_code}\n" \
  http://localhost:8070/reports/orders-by-status \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-MOCK-HTTP-STATUS: 500"
```

---

### `GET /reports/top-products`

**Simular 429 Too Many Requests (rate limiting):**
```bash
curl -s -w "\nHTTP %{http_code}\n" \
  "http://localhost:8070/reports/top-products?page=1&pageSize=10" \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-MOCK-HTTP-STATUS: 429"
```

---

### `GET /reports/average-ticket`

**Simular 404 Not Found:**
```bash
curl -s -w "\nHTTP %{http_code}\n" \
  http://localhost:8070/reports/average-ticket \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-MOCK-HTTP-STATUS: 404"
```

---

### `GET /reports/peak-hours`

**Simular 504 Gateway Timeout:**
```bash
curl -s -w "\nHTTP %{http_code}\n" \
  http://localhost:8070/reports/peak-hours \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-MOCK-HTTP-STATUS: 504"
```

---

### `GET /reports/delivery-performance`

**Simular 503 Service Unavailable:**
```bash
curl -s -w "\nHTTP %{http_code}\n" \
  http://localhost:8070/reports/delivery-performance \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "X-MOCK-HTTP-STATUS: 503"
```

---

### `POST /reports/batch/recalculate`

**Simular 409 Conflict (colisión de idempotencia):**
```bash
curl -s -w "\nHTTP %{http_code}\n" \
  -X POST http://localhost:8070/reports/batch/recalculate \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "Idempotency-Key: 00000000-0000-0000-0000-000000000003" \
  -H "X-MOCK-HTTP-STATUS: 409" \
  -d '{"from": "2024-01-01", "to": "2024-01-31"}'
```

**Simular 503 durante el encolado del job:**
```bash
curl -s -w "\nHTTP %{http_code}\n" \
  -X POST http://localhost:8070/reports/batch/recalculate \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: 00000000-0000-0000-0000-000000000001" \
  -H "X-Correlation-Id: 00000000-0000-0000-0000-000000000002" \
  -H "X-Consumer: bff-grupo1" \
  -H "Idempotency-Key: 00000000-0000-0000-0000-000000000003" \
  -H "X-MOCK-HTTP-STATUS: 503"
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

- El `MockStatusMiddleware` se aplica como el último middleware en la cadena de
  procesamiento (orden LIFO de Starlette), garantizando que sobreescribe el status
  code definitivo justo antes de devolver la respuesta al cliente.
- El body de la respuesta siempre refleja el procesamiento real del endpoint.
  Por ejemplo, al simular un `503` en `GET /reports/sales`, la respuesta tendrá
  `status_code=503` pero el body contendrá los datos reales de ventas.
- Esta herramienta está destinada exclusivamente a entornos de desarrollo y
  pruebas. **No debe activarse en producción.**
- El middleware registra eventos `DEBUG` por cada status code reemplazado y
  `WARNING` por cada header inválido o fuera de rango.
