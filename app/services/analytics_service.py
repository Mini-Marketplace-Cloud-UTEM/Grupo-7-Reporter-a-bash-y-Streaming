from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AggTopProduct, FactSalesSummary
from app.schemas.responses import (
    AverageTicketResponse,
    DeliveryPerformanceResponse,
    OrderStatusCount,
    PeakHourItem,
    Pagination,
    SalesPeriod,
    SalesReport,
    TopProduct,
    TopProductsResponse,
)


async def get_sales_report(
    db: AsyncSession,
    from_date: date | None,
    to_date: date | None,
) -> SalesReport:
    stmt = select(
        func.sum(FactSalesSummary.total_sales_amount),
        func.sum(FactSalesSummary.total_orders_count),
    )
    if from_date:
        stmt = stmt.where(FactSalesSummary.period_date >= datetime(from_date.year, from_date.month, from_date.day))
    if to_date:
        stmt = stmt.where(FactSalesSummary.period_date <= datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59))

    result = await db.execute(stmt)
    row = result.one()
    total_sales = int(row[0] or 0)
    total_orders = int(row[1] or 0)

    return SalesReport(
        period=SalesPeriod(**{"from": str(from_date) if from_date else None, "to": str(to_date) if to_date else None}),
        totalSales=total_sales,
        totalOrders=total_orders,
        currency="CLP",
    )


async def get_orders_by_status(db: AsyncSession) -> list[OrderStatusCount]:
    # fact_sales_summary no tiene columna de estado; se agrega desde logs de eventos.
    # Por ahora retorna datos desde una vista o query raw si existe, sino vacío.
    raw = await db.execute(text("SELECT status, COUNT(*) as count FROM order_status_log GROUP BY status"))
    rows = raw.fetchall()
    if not rows:
        return []
    return [OrderStatusCount(status=r[0], count=r[1]) for r in rows]


async def get_top_products(db: AsyncSession, page: int, page_size: int) -> TopProductsResponse:
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


async def get_average_ticket(db: AsyncSession) -> AverageTicketResponse:
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


async def get_peak_hours(db: AsyncSession) -> list[PeakHourItem]:
    raw = await db.execute(
        text(
            "SELECT EXTRACT(HOUR FROM period_date)::int AS hour, SUM(total_orders_count)::int AS order_count "
            "FROM fact_sales_summary GROUP BY hour ORDER BY hour"
        )
    )
    rows = raw.fetchall()
    return [PeakHourItem(hour=r[0], orderCount=r[1]) for r in rows]


async def get_delivery_performance(db: AsyncSession) -> DeliveryPerformanceResponse:
    raw = await db.execute(
        text(
            "SELECT AVG(delivery_time_minutes)::int, COUNT(*)::int "
            "FROM shipment_delivery_log"
        )
    )
    row = raw.fetchone()
    avg_time = int(row[0] or 0) if row else 0
    total_count = int(row[1] or 0) if row else 0
    return DeliveryPerformanceResponse(avgDeliveryTimeMinutes=avg_time, totalDeliveredCount=total_count)


async def upsert_sales_from_order(db: AsyncSession, period_date: datetime, amount: Decimal, correlation_id: str) -> None:
    existing = await db.execute(
        select(FactSalesSummary).where(
            func.date_trunc("day", FactSalesSummary.period_date) == func.date_trunc("day", period_date)
        )
    )
    record = existing.scalar_one_or_none()
    if record:
        record.total_sales_amount += amount
        record.total_orders_count += 1
        record.aggregation_type = "REAL_TIME"
        record.updated_at = datetime.now(timezone.utc)
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


async def upsert_top_product(db: AsyncSession, product_id: str, units: int, revenue: Decimal) -> None:
    existing = await db.execute(select(AggTopProduct).where(AggTopProduct.product_id == product_id))
    record = existing.scalar_one_or_none()
    if record:
        record.total_units_sold += units
        record.total_revenue_generated += revenue
        record.last_calculated_at = datetime.now(timezone.utc)
    else:
        db.add(AggTopProduct(product_id=product_id, total_units_sold=units, total_revenue_generated=revenue))
    await db.commit()
