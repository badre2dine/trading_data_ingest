from .celery_app import celery_app
from app.downloader import download
from app.tasks_loger import save_task_log
from app.db import SessionLocal
from datetime import datetime
import traceback
import os

# Define the output directory for parquet files

PARQUET_OUTPUT_DIR = os.getenv("PARQUET_OUTPUT_DIR", "./data")


@celery_app.task(bind=True)
def download_month(self, symbol, year, month, update=False):
    task_id = self.request.id
    db = SessionLocal()

    try:
        save_task_log(
            task_id,
            symbol,
            year,
            month,
            status="STARTED",
            start=datetime.now(),
        )
        download(
            symbol,
            year,
            month,
            interval="1m",
            out_dir=PARQUET_OUTPUT_DIR,
            update=update,
        )
        save_task_log(
            task_id,
            symbol,
            year,
            month,
            status="SUCCESS",
            end=datetime.now(),
            result="Done",
        )
    except Exception:
        save_task_log(
            task_id,
            symbol,
            year,
            month,
            status="FAILURE",
            end=datetime.now(),
            error=traceback.format_exc(),
        )

    db.close()
