
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import safe_extra, setup_logging
from app.core.middleware import StructuredLoggingMiddleware
from app.db.session import dispose_db, init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings)
    init_db(settings)
    logger.info(
        "application_started",
        extra=safe_extra(
            event_message="application_started",
            environment=settings.environment,
            version=settings.app_version,
        ),
    )
    try:
        yield
    finally:
        await dispose_db()
        logger.info(
            "application_stopped",
            extra=safe_extra(event_message="application_stopped"),
        )


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Store Intelligence API",
        version=settings.app_version,
        lifespan=lifespan,
    )
    application.add_middleware(StructuredLoggingMiddleware)
    application.include_router(api_router)
    return application


app = create_app()
