import json
import redis
from app.core.config import get_settings

_redis_client: redis.Redis | None = None

def get_redis_client() -> redis.Redis | None :
    global _redis_client
    if _redis_client is not None:
        return _redis_client


    settings = get_settings()
    try:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses = True,
            socket_timeout = 2.0,
            socket_connect_timeout = 2.0,
        )

        _redis_client.ping()
        return _redis_client
    except Exception as exc:
        print(f"[Redis Warning] Could not connect to Redis at {settings.redis_url}: {exc}")
        _redis_client = None
        return None


def is_redis_ready() -> bool:
    try:
        client = get_redis_client()
        return bool(client and client.ping())
    except Exception:
        return False    

def get_cache(key: str) -> dict | None:
    try:
        client = get_redis_client()
        if not client:
            return None
        raw_val = client.get(key)
        if raw_val:
            return json.loads(raw_val)
        return None
    except Exception as exc:
        print(f"[Redis Cache Error] Failed to read key '{key}': {exc}")
        return None

def set_cache(key: str, data: dict, expire_seconds: int = 86400) -> bool:
    try:
        client = get_redis_client()
        if not client:
            return False
        payload = json.dumps(data)
        return bool(client.set(key, payload, ex=expire_seconds))
    except Exception as exc:
        print(f"[Redis Cache Error] Failed to write key '{key}': {exc}")
        return False
