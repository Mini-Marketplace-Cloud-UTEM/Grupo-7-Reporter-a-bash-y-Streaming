"""
Modelos Pydantic para las respuestas de la API REST de Reportería.

Cada clase corresponde al schema de respuesta definido en el contrato OpenAPI
ubicado en marketplace-contracts/services/group-7-reporteria/openapi.yaml.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Formato estándar de error para todos los endpoints de la API."""

    timestamp: datetime = Field(..., description="Momento en que ocurrió el error (ISO 8601)")
    status: int = Field(..., description="Código HTTP de la respuesta")
    code: str = Field(..., description="Código interno del error (ej: INVALID_REQUEST)")
    message: str = Field(..., description="Descripción legible del error")
    correlationId: UUID | None = Field(
        None, description="ID de correlación del request que causó el error"
    )


class SalesPeriod(BaseModel):
    """Rango de fechas del período reportado."""

    from_: str | None = Field(
        None, alias="from", description="Fecha de inicio del período (YYYY-MM-DD)"
    )
    to: str | None = Field(None, description="Fecha de fin del período (YYYY-MM-DD)")

    model_config = {"populate_by_name": True}


class SalesReport(BaseModel):
    """Resumen financiero consolidado para el período solicitado."""

    period: SalesPeriod = Field(..., description="Rango de fechas del período analizado")
    totalSales: int = Field(..., description="Monto total de ventas en CLP")
    totalOrders: int = Field(..., description="Cantidad total de pedidos en el período")
    currency: str = Field("CLP", description="Moneda de los montos (siempre CLP)")


class OrderStatusCount(BaseModel):
    """Conteo de pedidos para un estado específico."""

    status: str = Field(..., description="Estado del pedido (ej: PENDING, CONFIRMED, DELIVERED)")
    count: int = Field(..., description="Cantidad de pedidos en ese estado")


class TopProduct(BaseModel):
    """Información de un producto en el ranking de más vendidos."""

    productId: str = Field(..., description="Identificador del producto (ej: P-100)")
    name: str | None = Field(None, description="Nombre del producto")
    unitsSold: int = Field(..., description="Total de unidades vendidas")
    revenue: int = Field(..., description="Ingresos generados en CLP")


class Pagination(BaseModel):
    """Metadatos de paginación para respuestas de listas."""

    totalItems: int = Field(..., description="Total de elementos en la colección completa")
    totalPages: int = Field(..., description="Número total de páginas disponibles")
    currentPage: int = Field(..., description="Página actual retornada")
    pageSize: int = Field(..., description="Cantidad de elementos por página")


class TopProductsResponse(BaseModel):
    """Respuesta paginada del ranking de productos más vendidos."""

    data: list[TopProduct] = Field(..., description="Lista de productos en la página actual")
    pagination: Pagination = Field(..., description="Metadatos de paginación")


class BatchRecalculateResponse(BaseModel):
    """Confirmación de encolado del proceso de recálculo batch."""

    jobId: UUID = Field(..., description="Identificador único del trabajo de recálculo")
    status: str = Field(
        "QUEUED", description="Estado inicial del trabajo (siempre QUEUED al crear)"
    )


class AverageTicketResponse(BaseModel):
    """Ticket promedio de compra calculado sobre el histórico completo."""

    averageTicket: int = Field(..., description="Valor promedio por pedido en CLP", example=49990)
    currency: str = Field("CLP", description="Moneda del monto (siempre CLP)")


class PeakHourItem(BaseModel):
    """Volumen de pedidos para una hora específica del día."""

    hour: int = Field(..., description="Hora del día en formato 24h (0–23)", example=18)
    orderCount: int = Field(
        ..., description="Cantidad de pedidos registrados en esa hora", example=42
    )


class DeliveryPerformanceResponse(BaseModel):
    """Métricas consolidadas de rendimiento del servicio de despacho."""

    avgDeliveryTimeMinutes: int = Field(
        ..., description="Tiempo promedio de entrega en minutos", example=120
    )
    totalDeliveredCount: int = Field(..., description="Total de envíos completados", example=154)
