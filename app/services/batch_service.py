import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID

from supabase import create_client
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.analytics import AggTopProduct, FactSalesSummary
from app.services.analytics_service import upsert_sales_from_order, upsert_top_product

logger = logging.getLogger(__name__)


async def run_batch_recalculate(db: AsyncSession, from_date: date | None, to_date: date | None, job_id: UUID) -> None:
    logger.info("batch_recalculate_start job_id=%s from=%s to=%s", job_id, from_date, to_date)
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        bucket = "event-logs"

        files = client.storage.from_(bucket).list()
        processed = 0

        for file_info in files:
            filename: str = file_info["name"]
            raw = client.storage.from_(bucket).download(filename)
            events = json.loads(raw)
            if not isinstance(events, list):
                events = [events]

            for event in events:
                event_type = event.get("eventType")
                payload = event.get("payload", {})
                correlation_id = event.get("correlationId", "")

                occurred_at_raw = event.get("occurredAt")
                try:
                    occurred_at = datetime.fromisoformat(occurred_at_raw) if occurred_at_raw else datetime.now(timezone.utc)
                except ValueError:
                    occurred_at = datetime.now(timezone.utc)

                if from_date and occurred_at.date() < from_date:
                    continue
                if to_date and occurred_at.date() > to_date:
                    continue

                if event_type == "OrderCreated":
                    amount = Decimal(str(payload.get("totalAmount", 0)))
                    await upsert_sales_from_order(db, occurred_at, amount, correlation_id)
                    processed += 1

                elif event_type == "PaymentApproved":
                    pass

        # Marcar registros del rango como BATCH_RECALCULATED
        from sqlalchemy import update, func as sa_func
        from app.models.analytics import FactSalesSummary

        stmt = (
            update(FactSalesSummary)
            .values(aggregation_type="BATCH_RECALCULATED", updated_at=datetime.now(timezone.utc))
        )
        if from_date:
            stmt = stmt.where(
                sa_func.date_trunc("day", FactSalesSummary.period_date)
                >= datetime(from_date.year, from_date.month, from_date.day)
            )
        if to_date:
            stmt = stmt.where(
                sa_func.date_trunc("day", FactSalesSummary.period_date)
                <= datetime(to_date.year, to_date.month, to_date.day)
            )
        await db.execute(stmt)
        await db.commit()

        logger.info("batch_recalculate_done job_id=%s processed_events=%d", job_id, processed)
    except Exception:
        logger.exception("batch_recalculate_error job_id=%s", job_id)
