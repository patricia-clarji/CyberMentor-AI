import asyncio

from app.core.config import Settings
from app.security.rate_limit import RateLimiter, policy_for


def test_local_rate_limit_adapter_enforces_window() -> None:
    async def exercise() -> None:
        settings = Settings(
            environment="development",
            database_url="sqlite+pysqlite:///:memory:",
            redis_url="redis://127.0.0.1:6399/0",
            email_backend="console",
        )
        limiter = RateLimiter(settings)
        first = await limiter.check("test:login", 2, 60)
        second = await limiter.check("test:login", 2, 60)
        blocked = await limiter.check("test:login", 2, 60)
        assert first.allowed is True
        assert second.allowed is True
        assert blocked.allowed is False
        assert blocked.retry_after > 0
        await limiter.close()

    asyncio.run(exercise())


def test_sensitive_endpoints_have_tighter_policies() -> None:
    assert policy_for("POST", "/api/v1/auth/login") == (10, 60)
    assert policy_for("POST", "/api/v1/auth/register") == (5, 60)
    assert policy_for("POST", "/api/v1/mentor/threads/x/messages") == (30, 60)
    assert policy_for("GET", "/api/v1/learning/dashboard") is None
