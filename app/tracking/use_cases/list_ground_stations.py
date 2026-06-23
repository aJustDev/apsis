from dataclasses import dataclass

from app.tracking.models import GroundStationORM
from app.tracking.repos import GroundStationRepo


@dataclass(slots=True)
class ListGroundStationsUseCase:
    ground_station_repo: GroundStationRepo

    async def execute(self) -> list[GroundStationORM]:
        return await self.ground_station_repo.list_all()


__all__ = ["ListGroundStationsUseCase"]
