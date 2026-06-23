from unittest.mock import AsyncMock

from app.tracking.repos import GroundStationRepo, SatelliteRepo
from app.tracking.use_cases.list_ground_stations import ListGroundStationsUseCase
from app.tracking.use_cases.list_satellites import ListSatellitesUseCase


async def test_list_ground_stations_delegates_to_repo() -> None:
    repo = AsyncMock(spec=GroundStationRepo)
    sentinel = [object(), object()]
    repo.list_all.return_value = sentinel

    use_case = ListGroundStationsUseCase(ground_station_repo=repo)
    assert await use_case.execute() is sentinel


async def test_list_satellites_paginates() -> None:
    repo = AsyncMock(spec=SatelliteRepo)
    repo.list_paginated.return_value = ([object()], 1)

    use_case = ListSatellitesUseCase(satellite_repo=repo)
    items, total = await use_case.execute(limit=10, offset=0)

    assert total == 1
    assert len(items) == 1
    repo.list_paginated.assert_awaited_once_with(limit=10, offset=0)
