"""
Servicio de consultas analíticas sobre Supabase Postgres.

Contiene la lógica de negocio para cada endpoint de reportería y las
funciones de upsert que el worker de Pub/Sub utiliza para actualizar
las métricas en tiempo real.
"""

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import (
    AggTopProduct,
    FactSalesSummary,
    InventoryShortageLog,
    OrderStatusLog,
    ShipmentDeliveryLog,
)
from app.schemas.responses import (
    AverageTicketResponse,
    DeliveryPerformanceResponse,
    OrderStatusCount,
    Pagination,
    PeakHourItem,
    SalesPeriod,
    SalesReport,
    TopProduct,
    TopProductsResponse,
)
from app.services import mock_data


async def get_sales_report(
    db: AsyncSession,
    from_date: date | None,
    to_date: date | None,
    use_mocks: bool = False,
) -> SalesReport:
    """Suma el total de ventas y pedidos dentro del rango de fechas indicado."""
    if use_mocks:
        return mock_data.sales_report(from_date, to_date)

    stmt = select(
        func.sum(FactSalesSummary.total_sales_amount),
        func.sum(FactSalesSummary.total_orders_count),
    )
    if from_date:
        stmt = stmt.where(
            FactSalesSummary.period_date >= datetime(from_date.year, from_date.month, from_date.day)
        )
    if to_date:
        stmt = stmt.where(
            FactSalesSummary.period_date
            <= datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59)
        )

    result = await db.execute(stmt)
    row = result.one()
    total_sales = int(row[0] or 0)
    total_orders = int(row[1] or 0)

    return SalesReport(
        period=SalesPeriod(
            **{
                "from": str(from_date) if from_date else None,
                "to": str(to_date) if to_date else None,
            }
        ),
        totalSales=total_sales,
        totalOrders=total_orders,
        currency="CLP",
    )


async def get_orders_by_status(db: AsyncSession, use_mocks: bool = False) -> list[OrderStatusCount]:
    """
    Retorna el conteo de pedidos agrupados por estado.

    Los datos provienen de order_status_log, tabla auxiliar poblada
    por el worker al procesar eventos OrderCreated y actualizaciones de estado.
    """
    if use_mocks:
        return mock_data.orders_by_status()

    raw = await db.execute(
        text("SELECT status, COUNT(*) as count FROM order_status_log GROUP BY status")
    )
    rows = raw.fetchall()
    if not rows:
        return []
    return [OrderStatusCount(status=r[0], count=r[1]) for r in rows]


async def get_top_products(db: AsyncSession, page: int, page_size: int, use_mocks: bool = False) -> TopProductsResponse:
    """Retorna el ranking paginado de productos ordenados por unidades vendidas."""
    if use_mocks:
        return mock_data.top_products(page, page_size)

    count_result = await db.execute(select(func.count()).select_from(AggTopProduct))
    total_items = count_result.scalar() or 0

    stmt = (
        select(AggTopProduct)
        .order_by(AggTopProduct.total_units_sold.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    products = result.scalars().all()

    # Techo entero para evitar que colecciones vacías retornen 0 páginas
    total_pages = max(1, -(-total_items // page_size))

    return TopProductsResponse(
        data=[
            TopProduct(
                productId=p.product_id,
                unitsSold=p.total_units_sold,
                revenue=int(p.total_revenue_generated),
            )
            for p in products
        ],
        pagination=Pagination(
            totalItems=total_items,
            totalPages=total_pages,
            currentPage=page,
            pageSize=page_size,
        ),
    )


async def get_average_ticket(db: AsyncSession, use_mocks: bool = False) -> AverageTicketResponse:
    """Calcula el ticket promedio como total_ventas / total_pedidos sobre el histórico completo."""
    if use_mocks:
        return mock_data.average_ticket()

    result = await db.execute(
        select(
            func.sum(FactSalesSummary.total_sales_amount),
            func.sum(FactSalesSummary.total_orders_count),
        )
    )
    row = result.one()
    total_sales = Decimal(row[0] or 0)
    total_orders = int(row[1] or 1)
    avg = int(total_sales / total_orders) if total_orders > 0 else 0
    return AverageTicketResponse(averageTicket=avg)


async def get_peak_hours(db: AsyncSession, use_mocks: bool = False) -> list[PeakHourItem]:
    """Agrupa la cantidad de pedidos por hora del día (0–23) según period_date."""
    if use_mocks:
        return mock_data.peak_hours()

    raw = await db.execute(
        text(
            "SELECT EXTRACT(HOUR FROM period_date)::int AS hour, SUM(total_orders_count)::int AS order_count "
            "FROM fact_sales_summary GROUP BY hour ORDER BY hour"
        )
    )
    rows = raw.fetchall()
    return [PeakHourItem(hour=r[0], orderCount=r[1]) for r in rows]


async def get_delivery_performance(db: AsyncSession, use_mocks: bool = False) -> DeliveryPerformanceResponse:
    """
    Retorna el tiempo promedio de entrega y el total de envíos completados.

    Los datos provienen de shipment_delivery_log, tabla auxiliar poblada
    por el worker al procesar eventos ShipmentDelivered.
    """
    if use_mocks:
        return mock_data.delivery_performance()

    raw = await db.execute(
        text("SELECT AVG(delivery_time_minutes)::int, COUNT(*)::int " "FROM shipment_delivery_log")
    )
    row = raw.fetchone()
    avg_time = int(row[0] or 0) if row else 0
    total_count = int(row[1] or 0) if row else 0
    return DeliveryPerformanceResponse(
        avgDeliveryTimeMinutes=avg_time, totalDeliveredCount=total_count
    )


async def upsert_sales_from_order(
    db: AsyncSession, period_date: datetime, amount: Decimal, correlation_id: str
) -> None:
    """
    Acumula ventas del día en fact_sales_summary (modo REAL_TIME).

    Si ya existe un registro para el mismo día lo incrementa;
    de lo contrario crea uno nuevo.
    """
    existing = await db.execute(
        select(FactSalesSummary).where(
            func.date_trunc("day", FactSalesSummary.period_date)
            == func.date_trunc("day", period_date)
        )
    )
    record = existing.scalar_one_or_none()
    if record:
        record.total_sales_amount += amount
        record.total_orders_count += 1
        record.aggregation_type = "REAL_TIME"
        # naive (sin tzinfo) para calzar con la columna TIMESTAMP WITHOUT TIME ZONE
        record.updated_at = datetime.now(UTC).replace(tzinfo=None)
    else:
        db.add(
            FactSalesSummary(
                period_date=period_date,
                total_sales_amount=amount,
                total_orders_count=1,
                aggregation_type="REAL_TIME",
            )
        )
    await db.commit()


async def upsert_top_product(
    db: AsyncSession, product_id: str, units: int, revenue: Decimal
) -> None:
    """Acumula unidades vendidas e ingresos por producto en agg_top_products."""
    existing = await db.execute(select(AggTopProduct).where(AggTopProduct.product_id == product_id))
    record = existing.scalar_one_or_none()
    if record:
        record.total_units_sold += units
        record.total_revenue_generated += revenue
        record.last_calculated_at = datetime.now(UTC).replace(tzinfo=None)
    else:
        db.add(
            AggTopProduct(
                product_id=product_id, total_units_sold=units, total_revenue_generated=revenue
            )
        )
    await db.commit()


async def insert_shipment_delivery(
    db: AsyncSession,
    shipment_id: str,
    order_id: str,
    delivered_at: datetime,
    city: str | None,
    delivery_time_minutes: int | None = None,
) -> None:
    """
    Guarda un envío entregado en shipment_delivery_log (modelo ORM ShipmentDeliveryLog).

    shipment_id es UNIQUE, así que antes de insertar verificamos que no exista:
    si el mismo envío llega dos veces (por un reintento), no se duplica el registro.
    """
    existing = await db.execute(
        select(ShipmentDeliveryLog).where(ShipmentDeliveryLog.shipment_id == shipment_id)
    )
    if existing.scalar_one_or_none() is not None:
        return  # ya estaba registrado: evitamos el duplicado (consistencia)

    db.add(
        ShipmentDeliveryLog(
            shipment_id=shipment_id,
            order_id=order_id,
            delivered_at=delivered_at,
            city=city,
            delivery_time_minutes=delivery_time_minutes,
        )
    )
    await db.commit()


async def insert_order_status(
    db: AsyncSession,
    order_id: str,
    status: str,
    occurred_at: datetime | None = None,
) -> None:
    """Anota el estado de un pedido en order_status_log (para /reports/orders-by-status)."""
    record = OrderStatusLog(order_id=order_id, status=status)
    if occurred_at is not None:
        record.occurred_at = occurred_at
    db.add(record)
    await db.commit()


async def insert_inventory_shortage(
    db: AsyncSession,
    product_id: str,
    current_stock: int,
    requested_quantity: int,
    occurred_at: datetime | None = None,
) -> None:
    """Guarda una alerta de quiebre de stock en inventory_shortage_log (modelo ORM)."""
    record = InventoryShortageLog(
        product_id=product_id,
        current_stock=current_stock,
        requested_quantity=requested_quantity,
    )
    if occurred_at is not None:
        record.occurred_at = occurred_at
    db.add(record)
    await db.commit()
