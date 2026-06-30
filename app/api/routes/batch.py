import uuid
from datetime import date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_headers_with_idempotency
from app.db.session import get_db
from app.models.analytics import BatchJob
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
    idempotency_key = UUID(_headers["idempotency_key"])
    from_date = body.from_ if body else None
    to_date = body.to if body else None

    # Verificar si la clave de idempotencia ya existe
    result = await db.execute(select(BatchJob).where(BatchJob.idempotency_key == idempotency_key))
    existing_job = result.scalar_one_or_none()

    if existing_job is not None:
        # Retornar el job existente sin re-encolar (idempotencia)
        return JSONResponse(
            status_code=200,
            content={"jobId": str(existing_job.job_id), "status": existing_job.status},
        )

    # Registrar el nuevo job en batch_jobs con estado QUEUED
    job_id = uuid.uuid4()
    new_job = BatchJob(
        idempotency_key=idempotency_key,
        job_id=job_id,
        status="QUEUED",
    )
    db.add(new_job)
    await db.commit()

    # Encolar la tarea en segundo plano
    background_tasks.add_task(
        run_batch_recalculate, db, from_date, to_date, job_id, idempotency_key
    )

    return BatchRecalculateResponse(jobId=job_id, status="QUEUED")
