import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.api.v1 import v1_router
from app.core.config import settings
from app.core.db import engine
from app.core.exceptions.handlers import register_exception_handlers

logger = logging.getLogger(__name__)


async def _database_reachable() -> bool:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        logger.warning("database unreachable at startup; readiness will report not-ready")
        return False
    return True


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # Los workers de jobs/outbox se arrancan aqui cuando existan; de momento
    # solo se publica el estado de la BD para el readiness probe.
    app.state.ready = await _database_reachable()
    yield
    await engine.dispose()


app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION, lifespan=lifespan)
register_exception_handlers(app)
app.include_router(v1_router)
