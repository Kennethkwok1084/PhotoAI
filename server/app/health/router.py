from pathlib import Path

import redis
from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.common.responses import ok
from app.config.settings import get_settings
from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    result = {"status": "ok", "db": "ok", "redis": "ok", "storage": "ok", "version": "0.1.0"}

    try:
        db.execute(text("SELECT 1"))
    except Exception:
        result["status"] = "degraded"
        result["db"] = "error"

    try:
        redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1).ping()
    except Exception:
        result["status"] = "degraded"
        result["redis"] = "error"

    try:
        root = Path(settings.storage_root)
        root.mkdir(parents=True, exist_ok=True)
        test_file = root / ".healthcheck"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink(missing_ok=True)
    except Exception:
        result["status"] = "degraded"
        result["storage"] = "error"

    return ok(request, result)

