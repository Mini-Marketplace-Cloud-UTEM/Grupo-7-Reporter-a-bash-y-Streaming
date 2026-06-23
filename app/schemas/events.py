"""
Modelos Pydantic para los eventos upstream consumidos desde Google Cloud Pub/Sub.

Todos los eventos siguen el envelope estándar del Mini Marketplace:
    eventId, eventType, version, occurredAt, producer, correlationId, payload
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventEnvelope(BaseModel):
    """Estructura estándar que envuelve todos los eventos del ecosistema."""

    eventId: str = Field(..., description="Identificador único del evento")
    eventType: str = Field(..., description="Tipo de evento (ej: OrderCreated)")
    version: str = Field("1.0", description="Versión del esquema del evento")
    occurredAt: datetime = Field(
        ..., description="Marca temporal de cuando ocurrió el evento (ISO 8601)"
    )
    producer: str = Field(..., description="Servicio que originó el evento")
    correlationId: UUID = Field(..., description="ID de correlación para trazabilidad distribuida")
    payload: dict[str, Any] = Field(..., description="Cuerpo específico del evento según su tipo")


class OrderCreatedPayload(BaseModel):
    """Payload del evento OrderCreated emitido por el Grupo 5 (Pedidos)."""

    orderId: str = Field(..., description="Identificador del pedido")
    totalAmount: Decimal = Field(..., description="Monto total del pedido en CLP")
    createdAt: datetime = Field(..., description="Fecha y hora de creación del pedido")
    customerId: str | None = Field(None, description="Identificador del cliente (opcional)")
    status: str | None = Field(None, description="Estado inicial del pedido")


class PaymentApprovedPayload(BaseModel):
    """Payload del evento PaymentApproved emitido por el Grupo 8 (Pagos)."""

    paymentId: str = Field(..., description="Identificador del pago aprobado")
    orderId: str = Field(..., description="Pedido asociado al pago")
    amountPaid: Decimal = Field(..., description="Monto efectivamente pagado en CLP")
    approvedAt: datetime | None = Field(None, description="Fecha y hora de aprobación del pago")


class InventoryShortagePayload(BaseModel):
    """Payload del evento InventoryShortage emitido por el Grupo 4 (Inventario)."""

    productId: str = Field(..., description="Identificador del producto con quiebre de stock")
    currentStock: int = Field(..., description="Stock actual disponible")
    requestedQuantity: int = Field(..., description="Cantidad solicitada que no pudo satisfacerse")
    occurredAt: datetime | None = Field(None, description="Momento en que se detectó el quiebre")


class ShipmentDeliveredPayload(BaseModel):
    """Payload del evento ShipmentDelivered emitido por el Grupo 6 (Despacho).

    Los campos usan snake_case según la convención del servicio de origen.
    """

    shipment_id: str = Field(..., description="Identificador del envío")
    order_id: str = Field(..., description="Pedido asociado al envío")
    delivered_at: datetime = Field(..., description="Fecha y hora de entrega efectiva")
    city: str | None = Field(None, description="Ciudad de destino del envío")
