import os


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./tasks.db")

CACHE_ENABLED: bool = _bool_env("CACHE_ENABLED", False)
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

TASK_CACHE_TTL: int = 60
LIST_CACHE_TTL: int = 30
