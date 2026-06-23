import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import settings
from app.core.db import async_session_factory
from app.core.events.dispatcher import dispatcher
from app.tracking.repos import GroundStationRepo, PassPredictionRepo, SatelliteRepo
from app.tracking.use_cases.compute_passes import ComputePassesUseCase

logger = logging.getLogger(__name__)


@dispatcher.register("tle.refreshed")
async def recompute_passes(payload: dict[str, Any]) -> None:
    """Recalcula los pasos de un satelite sobre todas las ground stations.

    Disparado por el outbox al actualizarse un TLE. Idempotente:
    ComputePassesUseCase borra y reinserta los pasos del par (sat, station),
    asi que reejecutar el handler converge al mismo estado.
    """
    satellite_id = uuid.UUID(payload["satellite_id"])
    async with async_session_factory() as session:
        ground_station_repo = GroundStationRepo(session)
        use_case = ComputePassesUseCase(
            satellite_repo=SatelliteRepo(session),
            ground_station_repo=ground_station_repo,
            pass_prediction_repo=PassPredictionRepo(session),
        )
        now = datetime.now(UTC)
        window = (now, now + timedelta(hours=settings.PASS_PREDICTION_HORIZON_HOURS))
        stations = await ground_station_repo.list_all()
        for station in stations:
            await use_case.execute(
                satellite_id=satellite_id, ground_station_id=station.id, window=window
            )
        await session.commit()
        logger.info(
            "recompute_passes: satellite %s over %d ground stations",
            satellite_id,
            len(stations),
        )
