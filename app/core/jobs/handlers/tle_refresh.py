import logging

from app.core.celestrak.exceptions import RateLimitedError
from app.core.celestrak.registry import celestrak_client_registry
from app.core.config import settings
from app.core.db import async_session_factory
from app.core.events.bus import EventBus
from app.core.jobs.registry import job_registry
from app.tracking.repos import SatelliteRepo
from app.tracking.use_cases.ingest_tles import IngestTlesUseCase

logger = logging.getLogger(__name__)


@job_registry.register("tle_refresh")
async def tle_refresh() -> None:
    client = celestrak_client_registry.get()
    async with async_session_factory() as session:
        use_case = IngestTlesUseCase(
            satellite_repo=SatelliteRepo(session),
            celestrak=client,
            event_bus=EventBus(session),
        )
        try:
            changed = await use_case.execute(group=settings.CELESTRAK_GROUP)
        except RateLimitedError:
            # CelesTrak recalcula los datos GP cada 2h; un 403 antes de tiempo
            # es un no-op limpio, no un fallo del job.
            logger.info("CelesTrak rate-limited; skipping TLE refresh")
            await session.rollback()
            return
        await session.commit()
        logger.info("tle_refresh upserted %d changed satellites", changed)
