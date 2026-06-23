from dataclasses import dataclass

from app.core.exceptions import ConflictError
from app.tracking.models import GroundStationORM
from app.tracking.repos import GroundStationRepo
from app.tracking.services.geometry import point_to_wkb


@dataclass(slots=True)
class RegisterGroundStationUseCase:
    ground_station_repo: GroundStationRepo

    async def execute(
        self, *, name: str, latitude: float, longitude: float, altitude_m: float
    ) -> GroundStationORM:
        if await self.ground_station_repo.get_by_name(name) is not None:
            raise ConflictError(f"ground station already exists: {name}")
        station = GroundStationORM(
            name=name,
            location=point_to_wkb(latitude=latitude, longitude=longitude),
            altitude_m=altitude_m,
        )
        return await self.ground_station_repo.create(station)


__all__ = ["RegisterGroundStationUseCase"]
