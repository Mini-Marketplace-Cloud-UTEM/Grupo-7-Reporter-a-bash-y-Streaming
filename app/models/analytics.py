"""
Modelos ORM de SQLAlchemy (async) para las tablas analíticas en Supabase Postgres.

Tablas:
    fact_sales_summary      — Agregaciones diarias de ventas (streaming y batch)
    agg_top_products        — Ranking acumulado de productos por unidades vendidas
    batch_jobs              — Control de idempotencia para el proceso batch de recálculo
    order_status_log        — Registro de cambios de estado de pedidos (eventos OrderCreated)
    shipment_delivery_log   — Registro de entregas de envíos (eventos ShipmentDelivered)
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
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


class BatchJob(Base):
    """
    Tabla de control de idempotencia para el proceso batch de recálculo.

    Cada `idempotency_key` queda registrada con su `job_id` y `status`
    para evitar ejecuciones duplicadas ante reintentos del cliente.
    Los estados posibles son: QUEUED, RUNNING, COMPLETED, FAILED.
    """

    __tablename__ = "batch_jobs"

    idempotency_key: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    job_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class OrderStatusLog(Base):
    """
    Tabla auxiliar que registra cambios de estado de pedidos.

    Poblada por el worker al procesar eventos OrderCreated y actualizaciones
    de estado. Se consulta en el endpoint de distribución de pedidos por estado.
    """

    __tablename__ = "order_status_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    order_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class ShipmentDeliveryLog(Base):
    """
    Tabla auxiliar que registra entregas de envíos completadas.

    Poblada por el worker al procesar eventos ShipmentDelivered. Se consulta
    en el endpoint de rendimiento de despacho (tiempo promedio y total de envíos).
    """

    __tablename__ = "shipment_delivery_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    shipment_id: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    order_id: Mapped[str] = mapped_column(String, nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    delivery_time_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
