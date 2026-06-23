import uuid
from dataclasses import dataclass
from datetime import datetime

from app.core.concurrency import run_blocking
from app.core.exceptions import NotFoundError
from app.tracking.models import PassPredictionORM
from app.tracking.repos import GroundStationRepo, PassPredictionRepo, SatelliteRepo
from app.tracking.services.geometry import linestring_to_wkb, wkb_to_lonlat
from app.tracking.services.passes import ObserverSite, compute_passes


@dataclass(slots=True)
class ComputePassesUseCase:
    """Recalcula y persiste los pasos de un satelite sobre una estacion.

    Borra las predicciones previas del par (satellite, station) y reinserta
    las nuevas. Lo invoca el handler de outbox cuando un TLE se actualiza y
    tambien se puede disparar a mano. La propagacion (skyfield, sync) corre
    via `run_blocking`.
    """

    satellite_repo: SatelliteRepo
    ground_station_repo: GroundStationRepo
    pass_prediction_repo: PassPredictionRepo

    async def execute(
        self,
        *,
        satellite_id: uuid.UUID,
        ground_station_id: uuid.UUID,
        window: tuple[datetime, datetime],
        min_elevation_deg: float = 10.0,
        track_samples: int = 24,
    ) -> int:
        satellite = await self.satellite_repo.get_by_id(satellite_id)
        if satellite is None:
            raise NotFoundError("Satellite", satellite_id)
        station = await self.ground_station_repo.get_by_id(ground_station_id)
        if station is None:
            raise NotFoundError("GroundStation", ground_station_id)

        longitude, latitude = wkb_to_lonlat(station.location)
        observer = ObserverSite(
            latitude=latitude, longitude=longitude, elevation_m=station.altitude_m
        )
        predicted = await run_blocking(
            compute_passes,
            line1=satellite.tle_line1,
            line2=satellite.tle_line2,
            observer=observer,
            window=window,
            min_elevation_deg=min_elevation_deg,
            track_samples=track_samples,
        )

        await self.pass_prediction_repo.delete_for_satellite_and_station(
            satellite_id, ground_station_id
        )
        for sat_pass in predicted:
            await self.pass_prediction_repo.create(
                PassPredictionORM(
                    satellite_id=satellite_id,
                    ground_station_id=ground_station_id,
                    aos_at=sat_pass.aos_at,
                    los_at=sat_pass.los_at,
                    peak_at=sat_pass.peak_at,
                    peak_elevation_deg=sat_pass.peak_elevation_deg,
                    track=linestring_to_wkb(sat_pass.ground_track),
                )
            )
        return len(predicted)


__all__ = ["ComputePassesUseCase"]
