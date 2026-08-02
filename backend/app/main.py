import logging
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from sqlalchemy import text

from app.api.v1.router import router
from app.core.config import get_settings
from app.core.errors import AppError, app_error_handler
from app.db.session import engine
from app.security.rate_limit import RateLimiter, policy_for

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = structlog.get_logger()
rate_limiter = RateLimiter(settings)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    log.info("application_started", environment=settings.environment)
    yield
    await rate_limiter.close()
    engine.dispose()
    log.info("application_stopped")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/api/docs" if settings.environment != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)
app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    fields = [
        {
            "location": ".".join(str(item) for item in error.get("loc", [])),
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "validation_error"),
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "request_validation_failed",
                "message": "The request contains invalid or missing fields.",
                "details": {"fields": fields},
                "requestId": request_id,
            }
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
)


@app.middleware("http")
async def request_context(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    started = time.perf_counter()
    policy = policy_for(request.method, request.url.path)
    response: Response
    if policy is not None:
        client_address = request.client.host if request.client else "unknown"
        decision = await rate_limiter.check(
            f"{client_address}:{request.url.path}",
            policy[0],
            policy[1],
        )
        if not decision.allowed:
            response = JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limited",
                        "message": "Too many requests. Try again shortly.",
                        "requestId": request_id,
                    }
                },
            )
            response.headers["Retry-After"] = str(decision.retry_after)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-Request-ID"] = request_id
            return response
    try:
        response = await call_next(request)
    except Exception:
        log.exception(
            "unhandled_request_error",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        response = JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "An unexpected error occurred.",
                    "requestId": request_id,
                }
            },
        )
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"
    )
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if policy is not None:
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    log.info(
        "http_request",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    return response


@app.get("/healthz", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz", tags=["operations"])
def ready() -> JSONResponse:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            table_names = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                        if engine.dialect.name == "sqlite"
                        else (
                            "SELECT table_name FROM information_schema.tables "
                            "WHERE table_schema = 'public'"
                        )
                    )
                )
            }
            required_tables = {
                "alembic_version",
                "skills",
                "assessments",
                "missions",
                "projects",
            }
            if not required_tables.issubset(table_names):
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "dependencies": {
                            "database": "ready",
                            "migrations": "required",
                            "seed": "unknown",
                        },
                    },
                )
            seed_checks = {
                "skills": connection.scalar(text("SELECT COUNT(*) FROM skills")) or 0,
                "diagnostics": connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM assessments "
                        "WHERE stable_key = 'junior-soc-diagnostic'"
                    )
                )
                or 0,
                "missions": connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM missions "
                        "WHERE stable_key = 'harbor-light-phishing-investigation'"
                    )
                )
                or 0,
                "projects": connection.scalar(
                    text(
                        "SELECT COUNT(*) FROM projects "
                        "WHERE stable_key = 'junior-soc-incident-escalation-project'"
                    )
                )
                or 0,
            }
            if (
                seed_checks["skills"] < 19
                or seed_checks["diagnostics"] != 1
                or seed_checks["missions"] != 1
                or seed_checks["projects"] != 1
            ):
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "dependencies": {
                            "database": "ready",
                            "migrations": "ready",
                            "seed": "required",
                        },
                    },
                )
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "dependencies": {
                    "database": "unavailable",
                    "migrations": "unknown",
                    "seed": "unknown",
                },
            },
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "ready",
            "dependencies": {
                "database": "ready",
                "migrations": "ready",
                "seed": "ready",
            },
        },
    )


app.include_router(router, prefix=settings.api_prefix)
