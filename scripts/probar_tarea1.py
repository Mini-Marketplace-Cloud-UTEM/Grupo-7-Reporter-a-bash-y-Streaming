"""
Script de prueba manual para el Rol 1 (persistencia del worker).

Simula la llegada de varios eventos sin necesitar Pub/Sub real: llama directamente
a los handlers del worker, que deben insertar las filas en las tablas de la base.

Uso (desde la raíz del proyecto, con la base levantada y el .env configurado):
    python -m scripts.probar_tarea1
"""

import asyncio

from app.workers.pubsub_consumer import (
    _handle_inventory_shortage,
    _handle_order_created,
    _handle_shipment_delivered,
)

# Pedidos creados con estado -> tablas fact_sales_summary (ventas) y order_status_log (estado).
# El estado alimenta /reports/orders-by-status.
pedidos = [
    {"orderId": "ORD-PRUEBA-001", "totalAmount": 19990, "createdAt": "2026-06-23T10:00:00", "status": "PENDING"},
    {"orderId": "ORD-PRUEBA-002", "totalAmount": 49990, "createdAt": "2026-06-23T12:30:00", "status": "PENDING"},
    {"orderId": "ORD-PRUEBA-003", "totalAmount": 89990, "createdAt": "2026-06-24T09:15:00", "status": "CONFIRMED"},
    {"orderId": "ORD-PRUEBA-004", "totalAmount": 12990, "createdAt": "2026-06-24T16:45:00", "status": "DELIVERED"},
]

# Varios envíos entregados -> tabla shipment_delivery_log.
# Cada shipment_id es único para que ninguno se ignore como duplicado.
# delivery_time_minutes queda NULL (se completa en el batch, según sugerencia de Fran).
envios = [
    {"shipment_id": "SHP-PRUEBA-001", "order_id": "ORD-PRUEBA-001", "delivered_at": "2026-06-23T15:00:00", "city": "Santiago"},
    {"shipment_id": "SHP-PRUEBA-002", "order_id": "ORD-PRUEBA-002", "delivered_at": "2026-06-23T16:30:00", "city": "Valparaíso"},
    {"shipment_id": "SHP-PRUEBA-003", "order_id": "ORD-PRUEBA-003", "delivered_at": "2026-06-24T09:15:00", "city": "Concepción"},
    {"shipment_id": "SHP-PRUEBA-004", "order_id": "ORD-PRUEBA-004", "delivered_at": "2026-06-24T11:45:00", "city": "La Serena"},
    {"shipment_id": "SHP-PRUEBA-005", "order_id": "ORD-PRUEBA-005", "delivered_at": "2026-06-24T18:20:00", "city": "Santiago"},
    {"shipment_id": "SHP-PRUEBA-006", "order_id": "ORD-PRUEBA-006", "delivered_at": "2026-06-25T10:05:00", "city": "Antofagasta"},
]

# Varios quiebres de stock -> tabla inventory_shortage_log.
quiebres = [
    {"productId": "P-PRUEBA-001", "currentStock": 0, "requestedQuantity": 3},
    {"productId": "P-PRUEBA-002", "currentStock": 1, "requestedQuantity": 5},
    {"productId": "P-PRUEBA-003", "currentStock": 0, "requestedQuantity": 2},
    {"productId": "P-PRUEBA-004", "currentStock": 2, "requestedQuantity": 8},
]


async def main() -> None:
    for pedido in pedidos:
        await _handle_order_created(pedido, "correlation-de-prueba")

    for envio in envios:
        await _handle_shipment_delivered(envio, "correlation-de-prueba")

    for quiebre in quiebres:
        await _handle_inventory_shortage(quiebre, "correlation-de-prueba")

    print(f"OK: {len(pedidos)} pedidos, {len(envios)} envíos y {len(quiebres)} quiebres procesados.")
    print("  En /docs puedes probar:")
    print(f"    GET /reports/orders-by-status   -> conteos por estado (PENDING, CONFIRMED, DELIVERED)")
    print(f"    GET /reports/delivery-performance -> totalDeliveredCount debería ser {len(envios)}")


if __name__ == "__main__":
    asyncio.run(main())
