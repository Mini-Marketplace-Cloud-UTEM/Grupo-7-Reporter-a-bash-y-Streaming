"""
Servicio de recálculo batch de agregaciones analíticas.

Lee los logs de eventos crudos desde el bucket 'event-logs' de Supabase Storage
y recalcula las métricas en Supabase Postgres. Actúa como mecanismo de failover
ante pérdida de mensajes en el canal de streaming (Pub/Sub).

Al finalizar, los registros del rango procesado quedan marcados como BATCH_RECALCULATED.
"""

import json
import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from supabase import create_client

from app.config import settings
from app.models.analytics import FactSalesSummary
from app.services.analytics_service import upsert_sales_from_order

logger = logging.getLogger(__name__)


async def run_batch_recalculate(
    db: AsyncSession, from_date: date | None, to_date: date | None, job_id: UUID
) -> None:
    """
    Ejecuta el recálculo completo de agregaciones para el rango de fechas indicado.

    Pasos:
        1. Lista todos los archivos de log en el bucket de Supabase Storage.
        2. Descarga y parsea cada archivo; filtra por rango de fechas si se especificó.
        3. Reproesa cada evento relevante actualizando las tablas analíticas.
        4. Marca los registros del rango como BATCH_RECALCULATED.
    """
    logger.info("recalculo_batch_inicio job_id=%s desde=%s hasta=%s", job_id, from_date, to_date)
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
                    occurred_at = (
                        datetime.fromisoformat(occurred_at_raw)
                        if occurred_at_raw
                        else datetime.now(UTC)
                    )
                except ValueError:
                    occurred_at = datetime.now(UTC)

                # Filtrar por rango de fechas si fue especificado en la solicitud
                if from_date and occurred_at.date() < from_date:
                    continue
                if to_date and occurred_at.date() > to_date:
                    continue

                if event_type == "OrderCreated":
                    amount = Decimal(str(payload.get("totalAmount", 0)))
                    await upsert_sales_from_order(db, occurred_at, amount, correlation_id)
                    processed += 1

                elif event_type == "PaymentApproved":
                    # Por ahora los pagos no modifican fact_sales_summary directamente
                    pass

        # Marcar todos los registros del rango como recalculados por proceso batch
        from sqlalchemy import func as sa_func
        from sqlalchemy import update

        stmt = update(FactSalesSummary).values(
            aggregation_type="BATCH_RECALCULATED", updated_at=datetime.now(UTC)
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

        logger.info("recalculo_batch_completado job_id=%s eventos_procesados=%d", job_id, processed)
    except Exception:
        logger.exception("recalculo_batch_error job_id=%s", job_id)
