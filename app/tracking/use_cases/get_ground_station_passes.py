import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from app.core.exceptions import NotFoundError
from app.tracking.repos import GroundStationRepo, PassPredictionRepo, SatelliteRepo
from app.tracking.services.geometry import wkb_to_geojson


@dataclass(frozen=True, slots=True)
class PassView:
    satellite_norad_id: int
    satellite_name: str
    aos_at: datetime
    los_at: datetime
    peak_at: datetime
    peak_elevation_deg: float
    track: dict[str, Any]  # GeoJSON LineString del ground-track


@dataclass(slots=True)
class GetGroundStationPassesUseCase:
    ground_station_repo: GroundStationRepo
    pass_prediction_repo: PassPredictionRepo
    satellite_repo: SatelliteRepo

    async def execute(
        self, *, ground_station_id: uuid.UUID, after: datetime
    ) -> list[PassView]:
        station = await self.ground_station_repo.get_by_id(ground_station_id)
        if station is None:
            raise NotFoundError("GroundStation", ground_station_id)

        predictions = await self.pass_prediction_repo.list_for_ground_station(
            ground_station_id, after=after
        )
        satellites = {sat.id: sat for sat in await self.satellite_repo.list_all()}
        return [
            PassView(
                satellite_norad_id=satellites[prediction.satellite_id].norad_id,
                satellite_name=satellites[prediction.satellite_id].name,
                aos_at=prediction.aos_at,
                los_at=prediction.los_at,
                peak_at=prediction.peak_at,
                peak_elevation_deg=prediction.peak_elevation_deg,
                track=wkb_to_geojson(prediction.track),
            )
            for prediction in predictions
        ]


__all__ = ["GetGroundStationPassesUseCase", "PassView"]
