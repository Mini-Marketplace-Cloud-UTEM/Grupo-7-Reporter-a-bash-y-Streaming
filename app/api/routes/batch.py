import uuid
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_headers_with_idempotency
from app.db.session import get_db
from app.schemas.responses import BatchRecalculateResponse
from app.services.batch_service import run_batch_recalculate

router = APIRouter(prefix="/reports", tags=["Reportes"])


class BatchRecalculateRequest(BaseModel):
    """Parámetros opcionales de rango de fechas para acotar el recálculo batch."""

    from_: date | None = Field(
        None, alias="from", description="Fecha de inicio del rango a recalcular (YYYY-MM-DD)"
    )
    to: date | None = Field(None, description="Fecha de fin del rango a recalcular (YYYY-MM-DD)")

    model_config = {"populate_by_name": True}


@router.post(
    "/batch/recalculate",
    response_model=BatchRecalculateResponse,
    status_code=202,
    summary="Forzar recálculo batch (asíncrono)",
    description=(
        "Encola un recálculo completo de las agregaciones analíticas leyendo los logs crudos "
        "almacenados en Supabase Storage. Retorna inmediatamente con estado QUEUED; "
        "el proceso corre en segundo plano. Requiere Idempotency-Key para evitar ejecuciones duplicadas. "
        "Al finalizar, los registros del rango quedan marcados como BATCH_RECALCULATED."
    ),
)
async def trigger_batch_recalculate(
    body: BatchRecalculateRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _headers: dict = Depends(require_headers_with_idempotency),
    db: AsyncSession = Depends(get_db),
):
    job_id = uuid.uuid4()
    from_date = body.from_ if body else None
    to_date = body.to if body else None
    background_tasks.add_task(run_batch_recalculate, db, from_date, to_date, job_id)
    return BatchRecalculateResponse(jobId=job_id, status="QUEUED")
