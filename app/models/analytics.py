from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FactSalesSummary(Base):
    __tablename__ = "fact_sales_summary"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    period_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_sales_amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    total_orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    aggregation_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        info={"check": "aggregation_type IN ('REAL_TIME', 'BATCH_RECALCULATED')"},
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("aggregation_type IN ('REAL_TIME', 'BATCH_RECALCULATED')", name="ck_aggregation_type"),
    )


class AggTopProduct(Base):
    __tablename__ = "agg_top_products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    total_units_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_revenue_generated: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    last_calculated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
