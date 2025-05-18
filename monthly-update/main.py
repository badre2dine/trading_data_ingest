import datetime


from app.db import SessionLocal
from app.models import PairStreamerStatus
from worker.tasks import download_month

db = SessionLocal()
paris = []
try:
    pairs = [
        s.pair for s in db.query(PairStreamerStatus).all() if s.status == "activate"
    ]
finally:
    db.close()

current = datetime.datetime.now() - datetime.timedelta(hours=1)
for pair in pairs:
    task = download_month.delay(pair, current.year, current.month, update=True)
    print(f"Task {task.id} for {pair} {current.year}-{current.month:02d} submitted")
