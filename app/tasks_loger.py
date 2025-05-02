from app.db import SessionLocal
from app.models import TaskLog


def save_task_log(
    task_id, symbol, year, month, status, start=None, end=None, result=None, error=None
):
    db = SessionLocal()
    log = TaskLog(
        task_id=task_id,
        symbol=symbol,
        year=year,
        month=month,
        status=status,
        start_time=start,
        end_time=end,
        result=result,
        error=error,
    )
    db.merge(log)
    db.commit()
    db.close()
