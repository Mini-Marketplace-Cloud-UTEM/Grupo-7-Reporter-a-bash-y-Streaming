import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.events import EventEnvelope


def _make_envelope(event_type: str, payload: dict) -> dict:
    return {
        "eventId": str(uuid.uuid4()),
        "eventType": event_type,
        "version": "1.0",
        "occurredAt": datetime.now(timezone.utc).isoformat(),
        "producer": "test",
        "correlationId": str(uuid.uuid4()),
        "payload": payload,
    }


def test_envelope_parse_order_created():
    raw = _make_envelope("OrderCreated", {"orderId": "ORD-001", "totalAmount": "49990", "createdAt": datetime.now(timezone.utc).isoformat()})
    envelope = EventEnvelope(**raw)
    assert envelope.eventType == "OrderCreated"
    assert envelope.payload["orderId"] == "ORD-001"


def test_envelope_parse_payment_approved():
    raw = _make_envelope("PaymentApproved", {"paymentId": "PAY-001", "orderId": "ORD-001", "amountPaid": "49990"})
    envelope = EventEnvelope(**raw)
    assert envelope.eventType == "PaymentApproved"


def test_envelope_parse_inventory_shortage():
    raw = _make_envelope("InventoryShortage", {"productId": "P-100", "currentStock": 2, "requestedQuantity": 5})
    envelope = EventEnvelope(**raw)
    assert envelope.eventType == "InventoryShortage"


def test_envelope_parse_shipment_delivered():
    raw = _make_envelope(
        "ShipmentDelivered",
        {"shipment_id": "SHP-001", "order_id": "ORD-001", "delivered_at": datetime.now(timezone.utc).isoformat(), "city": "Santiago"},
    )
    envelope = EventEnvelope(**raw)
    assert envelope.eventType == "ShipmentDelivered"
