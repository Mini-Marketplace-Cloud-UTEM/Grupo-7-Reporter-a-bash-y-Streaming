from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_use_mocks, require_headers
from app.db.session import get_db
from app.schemas.responses import (
    AverageTicketResponse,
    DeliveryPerformanceResponse,
    OrderStatusCount,
    PeakHourItem,
    SalesReport,
    TopProductsResponse,
)
from app.services import analytics_service

router = APIRouter(prefix="/reports", tags=["Reportes"])


@router.get(
    "/sales",
    response_model=SalesReport,
    summary="Resumen financiero consolidado",
    description=(
        "Retorna el total de ventas y cantidad de pedidos para un período dado. "
        "Si no se especifican fechas, consolida todo el histórico disponible. "
        "La moneda siempre es CLP."
    ),
)
async def get_sales_report(
    from_: date | None = Query(
        None, alias="from", description="Fecha de inicio del período (YYYY-MM-DD)"
    ),
    to: date | None = Query(None, description="Fecha de fin del período (YYYY-MM-DD)"),
    _headers: dict = Depends(require_headers),
    db: AsyncSession = Depends(get_db),
    use_mocks: bool = Depends(get_use_mocks),
):
    return await analytics_service.get_sales_report(db, from_, to, use_mocks=use_mocks)


@router.get(
    "/orders-by-status",
    response_model=list[OrderStatusCount],
    summary="Conteo de pedidos por estado",
    description=(
        "Retorna una lista con la cantidad de pedidos agrupados por estado "
        "(por ejemplo: PENDING, CONFIRMED, DELIVERED). "
        "Los datos se obtienen del log de estados registrado por el worker de Pub/Sub."
    ),
)
async def get_orders_by_status(
    _headers: dict = Depends(require_headers),
    db: AsyncSession = Depends(get_db),
    use_mocks: bool = Depends(get_use_mocks),
):
    # TODO(avance-3): Este endpoint requiere que el worker _handle_order_created
    # también inserte en order_status_log. Coordinar con Rol 1 (Agustín).
    return await analytics_service.get_orders_by_status(db, use_mocks=use_mocks)


@router.get(
    "/top-products",
    response_model=TopProductsResponse,
    summary="Productos más vendidos",
    description=(
        "Retorna una lista paginada de productos ordenados por unidades vendidas de mayor a menor. "
        "Usa los parámetros `page` y `pageSize` para navegar entre páginas."
    ),
)
async def get_top_products(
    page: int = Query(1, ge=1, description="Número de página (comienza en 1)"),
    pageSize: int = Query(
        20, ge=1, le=100, description="Cantidad de productos por página (máximo 100)"
    ),
    _headers: dict = Depends(require_headers),
    db: AsyncSession = Depends(get_db),
    use_mocks: bool = Depends(get_use_mocks),
):
    return await analytics_service.get_top_products(db, page, pageSize, use_mocks=use_mocks)


@router.get(
    "/average-ticket",
    response_model=AverageTicketResponse,
    summary="Ticket promedio de compra",
    description=(
        "Calcula el ticket promedio dividiendo el monto total de ventas entre la cantidad de pedidos. "
        "El valor se expresa en pesos chilenos (CLP)."
    ),
)
async def get_average_ticket(
    _headers: dict = Depends(require_headers),
    db: AsyncSession = Depends(get_db),
    use_mocks: bool = Depends(get_use_mocks),
):
    return await analytics_service.get_average_ticket(db, use_mocks=use_mocks)


@router.get(
    "/peak-hours",
    response_model=list[PeakHourItem],
    summary="Franjas horarias con mayor volumen de transacciones",
    description=(
        "Analiza la distribución horaria de pedidos agrupando por hora del día (0–23). "
        "Útil para identificar los momentos de mayor demanda en el marketplace."
    ),
)
async def get_peak_hours(
    _headers: dict = Depends(require_headers),
    db: AsyncSession = Depends(get_db),
    use_mocks: bool = Depends(get_use_mocks),
):
    return await analytics_service.get_peak_hours(db, use_mocks=use_mocks)


@router.get(
    "/delivery-performance",
    response_model=DeliveryPerformanceResponse,
    summary="Tiempos promedio de entrega (Lead Time)",
    description=(
        "Consolida las métricas de despacho: tiempo promedio de entrega en minutos "
        "y cantidad total de envíos completados, calculados a partir de los eventos ShipmentDelivered."
    ),
)
async def get_delivery_performance(
    _headers: dict = Depends(require_headers),
    db: AsyncSession = Depends(get_db),
    use_mocks: bool = Depends(get_use_mocks),
):
    return await analytics_service.get_delivery_performance(db, use_mocks=use_mocks)
