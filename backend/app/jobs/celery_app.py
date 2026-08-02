from datetime import UTC, datetime

from celery import Celery  # type: ignore[import-untyped]
from sqlalchemy import delete

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.identity import Session

settings = get_settings()
celery_app = Celery(
    "cybermentor",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_time_limit=120,
    task_soft_time_limit=90,
    worker_prefetch_multiplier=1,
)


def cleanup_expired_sessions_impl(now: datetime | None = None) -> int:
    cutoff = now or datetime.now(UTC)
    with SessionLocal() as db:
        result = db.execute(
            delete(Session).where(
                Session.expires_at < cutoff,
            )
        )
        db.commit()
        return int(result.rowcount or 0)


@celery_app.task(name="cybermentor.cleanup_expired_sessions")  # type: ignore[untyped-decorator]
def cleanup_expired_sessions() -> dict[str, int | str]:
    removed = cleanup_expired_sessions_impl()
    return {"status": "completed", "removed": removed}
