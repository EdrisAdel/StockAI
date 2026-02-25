import json
from typing import Any

import redis

from app.config import settings


redis_client = redis.Redis.from_url(settings.redis_url, decode_responses=True)


def cache_get(key: str) -> Any | None:
    value = redis_client.get(key)
    if value is None:
        return None
    return json.loads(value)


def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))
