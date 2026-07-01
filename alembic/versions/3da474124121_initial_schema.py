"""initial_schema

Revision ID: 3da474124121
Revises:
Create Date: 2026-06-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "3da474124121"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fact_sales_summary",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("period_date", sa.DateTime(), nullable=False),
        sa.Column("total_sales_amount", sa.Numeric(), nullable=False),
        sa.Column("total_orders_count", sa.Integer(), nullable=False),
        sa.Column("aggregation_type", sa.String(length=20), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "aggregation_type IN ('REAL_TIME', 'BATCH_RECALCULATED')",
            name="ck_aggregation_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_fact_sales_period", "fact_sales_summary", ["period_date"])

    op.create_table(
        "agg_top_products",
        sa.Column("product_id", sa.String(), nullable=False),
        sa.Column("total_units_sold", sa.Integer(), nullable=False),
        sa.Column("total_revenue_generated", sa.Numeric(), nullable=False),
        sa.Column(
            "last_calculated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("product_id"),
    )
    op.create_index(
        "idx_agg_top_products_units",
        "agg_top_products",
        [sa.text("total_units_sold DESC")],
    )

    op.create_table(
        "order_status_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_order_status_log_status", "order_status_log", ["status"])

    op.create_table(
        "shipment_delivery_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("shipment_id", sa.String(), nullable=False),
        sa.Column("order_id", sa.String(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("delivery_time_minutes", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shipment_id"),
    )

    op.create_table(
        "batch_jobs",
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="QUEUED"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("idempotency_key"),
    )


def downgrade() -> None:
    op.drop_table("batch_jobs")
    op.drop_index("idx_order_status_log_status", table_name="order_status_log")
    op.drop_table("order_status_log")
    op.drop_index("idx_agg_top_products_units", table_name="agg_top_products")
    op.drop_table("agg_top_products")
    op.drop_index("idx_fact_sales_period", table_name="fact_sales_summary")
    op.drop_table("fact_sales_summary")
    op.drop_table("shipment_delivery_log")
