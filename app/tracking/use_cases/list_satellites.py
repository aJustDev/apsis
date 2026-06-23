from dataclasses import dataclass

from app.tracking.models import SatelliteORM
from app.tracking.repos import SatelliteRepo


@dataclass(slots=True)
class ListSatellitesUseCase:
    satellite_repo: SatelliteRepo

    async def execute(
        self, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[SatelliteORM], int]:
        return await self.satellite_repo.list_paginated(limit=limit, offset=offset)


__all__ = ["ListSatellitesUseCase"]
