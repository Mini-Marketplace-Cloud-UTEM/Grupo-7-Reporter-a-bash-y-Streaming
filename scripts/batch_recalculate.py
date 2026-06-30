"""
Script standalone de recálculo batch — ejecutado por GitHub Actions (cron nocturno).

Uso:
    python scripts/batch_recalculate.py [--from YYYY-MM-DD] [--to YYYY-MM-DD]

Ejemplos:
    python scripts/batch_recalculate.py --from 2025-06-01 --to 2025-06-30
    python scripts/batch_recalculate.py   # recalcula todo el histórico
"""

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.db.session import AsyncSessionLocal  # noqa: E402
from app.services.batch_service import run_batch_recalculate  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def parse_date(value: str) -> date:
    """Convierte una cadena YYYY-MM-DD a objeto date."""
    return date.fromisoformat(value)


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recalcula las agregaciones analíticas desde los logs almacenados en Supabase Storage."
    )
    parser.add_argument(
        "--from",
        dest="from_date",
        type=parse_date,
        default=None,
        help="Fecha de inicio (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--to", dest="to_date", type=parse_date, default=None, help="Fecha de fin (YYYY-MM-DD)"
    )
    args = parser.parse_args()

    job_id = uuid.uuid4()
    logging.info(
        "Iniciando recálculo batch job_id=%s desde=%s hasta=%s",
        job_id,
        args.from_date,
        args.to_date,
    )

    async with AsyncSessionLocal() as db:
        processed = await run_batch_recalculate(db, args.from_date, args.to_date, job_id)

    logging.info("Recálculo batch completado job_id=%s eventos_procesados=%d", job_id, processed)
    print(f"job_id={job_id} eventos_procesados={processed}")


if __name__ == "__main__":
    asyncio.run(main())
