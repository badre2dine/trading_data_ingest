import redis
import json
from datetime import datetime
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def write_to_redis(key: str, row: dict):

    r.zadd(key, {json.dumps(row): row["timestamp"]})


def cleanup_old_data(key: str):
    cutoff = datetime.now().timestamp() - 3600  # 1 hour ago
    r.zremrangebyscore(key, 0, cutoff)
