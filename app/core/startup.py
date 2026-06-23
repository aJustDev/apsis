import asyncio
import logging
import os
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import settings

logger = logging.getLogger(__name__)

DB_CONNECT_TIMEOUT = 3


def check_utc_timezone() -> None:
    """Verifica que el proceso opera en UTC. Fail-fast en prod.

    El calculo de pasos compara timestamptz con now() (edad del TLE, ventanas
    AOS/LOS); el cliente debe leer y escribir en UTC para que la comparacion
    sea estable. En dev se advierte; en prod se aborta el arranque.
    """
    local_tz = (time.tzname[0] or "").upper() if time.tzname else ""
    env_tz = (os.environ.get("TZ") or "").upper()
    utc_variants = {"UTC", "GMT", "UCT", "UNIVERSAL", ""}
    is_utc = local_tz in utc_variants or env_tz == "UTC"
    if is_utc:
        return

    message = (
        f"Process timezone is not UTC (tzname={time.tzname}, TZ={env_tz}). "
        "Set TZ=UTC in the deploy environment."
    )
    if settings.ENVIRONMENT == "prod":
        raise RuntimeError(message)
    logger.warning(message)


async def check_database(engine: AsyncEngine) -> str:
    try:
        async with asyncio.timeout(DB_CONNECT_TIMEOUT), engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "OK"
    except Exception as exc:
        logger.warning("database not available: %s", exc)
        return "UNAVAILABLE"


__all__ = ["check_database", "check_utc_timezone"]
