"""
Modelos ORM de SQLAlchemy (async) para las tablas analíticas en Supabase Postgres.

Tablas:
    fact_sales_summary    — Agregaciones diarias de ventas (streaming y batch)
    agg_top_products      — Ranking acumulado de productos por unidades vendidas
    shipment_delivery_log — Registro de envíos entregados (métricas de despacho)
    inventory_shortage_log — Registro de quiebres de stock (alertas)
    order_status_log       — Registro del estado de los pedidos
"""

import uuid
from datetime import datetime
from decimal import Decimal

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


class ShipmentDeliveryLog(Base):
    """
    Registro de envíos entregados, poblado por el worker al procesar
    eventos ShipmentDelivered. Fuente del endpoint /reports/delivery-performance.

    Calcado a migrations/001_initial_schema.sql (tabla shipment_delivery_log).
    """

    __tablename__ = "shipment_delivery_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    order_id: Mapped[str] = mapped_column(String, nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class OrderStatusLog(Base):
    """
    Registro del estado de los pedidos, poblado por el worker al procesar
    eventos OrderCreated (cuando traen status). Fuente del endpoint
    /reports/orders-by-status.

    Calcado a migrations/001_initial_schema.sql (tabla order_status_log).
    """

    __tablename__ = "order_status_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class InventoryShortageLog(Base):
    """
    Registro de quiebres de stock, poblado por el worker al procesar
    eventos InventoryShortage. Alimenta las alertas del panel del administrador.

    Calcado a migrations/002_inventory_shortage.sql (tabla inventory_shortage_log).
    """

    __tablename__ = "inventory_shortage_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    product_id: Mapped[str] = mapped_column(String, nullable=False)
    current_stock: Mapped[int] = mapped_column(Integer, nullable=False)
    requested_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
