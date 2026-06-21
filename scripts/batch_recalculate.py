"""
Script standalone para recálculo batch — ejecutado por GitHub Actions (cron nocturno).
Uso: python scripts/batch_recalculate.py [--from YYYY-MM-DD] [--to YYYY-MM-DD]
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

from app.db.session import AsyncSessionLocal
from app.services.batch_service import run_batch_recalculate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def parse_date(value: str) -> date:
    return date.fromisoformat(value)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Batch recalculate analytics")
    parser.add_argument("--from", dest="from_date", type=parse_date, default=None)
    parser.add_argument("--to", dest="to_date", type=parse_date, default=None)
    args = parser.parse_args()

    job_id = uuid.uuid4()
    logging.info("Starting batch recalculate job_id=%s from=%s to=%s", job_id, args.from_date, args.to_date)

    async with AsyncSessionLocal() as db:
        await run_batch_recalculate(db, args.from_date, args.to_date, job_id)

    logging.info("Batch recalculate completed job_id=%s", job_id)


if __name__ == "__main__":
    asyncio.run(main())
