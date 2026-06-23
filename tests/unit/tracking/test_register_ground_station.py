from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import ConflictError
from app.tracking.repos import GroundStationRepo
from app.tracking.services.geometry import wkb_to_lonlat
from app.tracking.use_cases.register_ground_station import RegisterGroundStationUseCase


async def test_register_creates_station_with_point() -> None:
    repo = AsyncMock(spec=GroundStationRepo)
    repo.get_by_name.return_value = None
    repo.create.side_effect = lambda entity: entity

    use_case = RegisterGroundStationUseCase(ground_station_repo=repo)
    station = await use_case.execute(
        name="Madrid", latitude=40.4168, longitude=-3.7038, altitude_m=667.0
    )

    assert station.name == "Madrid"
    lon, lat = wkb_to_lonlat(station.location)
    assert lon == pytest.approx(-3.7038)
    assert lat == pytest.approx(40.4168)
    repo.create.assert_awaited_once()


async def test_register_duplicate_name_raises_conflict() -> None:
    repo = AsyncMock(spec=GroundStationRepo)
    repo.get_by_name.return_value = object()  # ya existe

    use_case = RegisterGroundStationUseCase(ground_station_repo=repo)
    with pytest.raises(ConflictError):
        await use_case.execute(name="Madrid", latitude=0.0, longitude=0.0, altitude_m=0.0)
