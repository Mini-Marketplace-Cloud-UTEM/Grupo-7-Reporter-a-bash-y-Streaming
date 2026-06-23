"""
Pruebas unitarias para el parseo de eventos upstream.

Verifica que el EventEnvelope y los payloads específicos de cada tipo
de evento sean correctamente deserializados por los modelos Pydantic.
"""

import uuid
from datetime import UTC, datetime

from app.schemas.events import EventEnvelope


def _construir_envelope(tipo_evento: str, payload: dict) -> dict:
    """Construye un envelope de evento con datos de prueba."""
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": tipo_evento,
        "version": "1.0",
        "occurredAt": datetime.now(UTC).isoformat(),
        "producer": "test",
        "correlationId": str(uuid.uuid4()),
        "payload": payload,
    }


def test_parseo_order_created():
    """El envelope de OrderCreated debe deserializarse con el tipo y orderId correctos."""
    raw = _construir_envelope(
        "OrderCreated",
        {"orderId": "ORD-001", "totalAmount": "49990", "createdAt": datetime.now(UTC).isoformat()},
    )
    envelope = EventEnvelope(**raw)
    assert envelope.eventType == "OrderCreated"
    assert envelope.payload["orderId"] == "ORD-001"


def test_parseo_payment_approved():
    """El envelope de PaymentApproved debe deserializarse correctamente."""
    raw = _construir_envelope(
        "PaymentApproved", {"paymentId": "PAY-001", "orderId": "ORD-001", "amountPaid": "49990"}
    )
    envelope = EventEnvelope(**raw)
    assert envelope.eventType == "PaymentApproved"


def test_parseo_inventory_shortage():
    """El envelope de InventoryShortage debe deserializarse correctamente."""
    raw = _construir_envelope(
        "InventoryShortage", {"productId": "P-100", "currentStock": 2, "requestedQuantity": 5}
    )
    envelope = EventEnvelope(**raw)
    assert envelope.eventType == "InventoryShortage"


def test_parseo_shipment_delivered():
    """El envelope de ShipmentDelivered debe deserializarse con los campos en snake_case."""
    raw = _construir_envelope(
        "ShipmentDelivered",
        {
            "shipment_id": "SHP-001",
            "order_id": "ORD-001",
            "delivered_at": datetime.now(UTC).isoformat(),
            "city": "Santiago",
        },
    )
    envelope = EventEnvelope(**raw)
    assert envelope.eventType == "ShipmentDelivered"
