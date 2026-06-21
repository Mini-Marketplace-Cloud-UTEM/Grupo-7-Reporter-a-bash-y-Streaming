"""
Modelos ORM de SQLAlchemy (async) para las tablas analíticas en Supabase Postgres.

Tablas:
    fact_sales_summary  — Agregaciones diarias de ventas (streaming y batch)
    agg_top_products    — Ranking acumulado de productos por unidades vendidas
"""

from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class FactSalesSummary(Base):
    """
    Tabla de hechos para el resumen diario de ventas.

    El campo aggregation_type distingue si el registro fue cargado
    en tiempo real por el worker de Pub/Sub ('REAL_TIME') o recalculado
    desde los logs fríos en Supabase Storage ('BATCH_RECALCULATED').
    """

    __tablename__ = "fact_sales_summary"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    period_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    total_sales_amount: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    total_orders_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    aggregation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            "aggregation_type IN ('REAL_TIME', 'BATCH_RECALCULATED')",
            name="ck_aggregation_type",
        ),
    )


class AggTopProduct(Base):
    """
    Tabla de agregación acumulada de productos más vendidos.

    Se actualiza en caliente ante cada evento OrderCreated y se recalcula
    íntegramente durante el proceso batch nocturno.
    """

    __tablename__ = "agg_top_products"

    product_id: Mapped[str] = mapped_column(String, primary_key=True)
    total_units_sold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_revenue_generated: Mapped[Decimal] = mapped_column(Numeric, nullable=False, default=0)
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
