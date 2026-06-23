import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.core.exceptions import NotFoundError
from app.tracking.models import PassPredictionORM, SatelliteORM
from app.tracking.repos import GroundStationRepo, PassPredictionRepo, SatelliteRepo
from app.tracking.services.geometry import linestring_to_wkb
from app.tracking.use_cases.get_ground_station_passes import GetGroundStationPassesUseCase


async def test_get_passes_maps_geojson_and_satellite_info() -> None:
    satellite_id = uuid.uuid4()
    station_id = uuid.uuid4()
    satellite = SatelliteORM(
        norad_id=25544,
        name="ISS (ZARYA)",
        tle_line1="1",
        tle_line2="2",
        epoch=datetime(2024, 1, 1, tzinfo=UTC),
    )
    satellite.id = satellite_id
    prediction = PassPredictionORM(
        satellite_id=satellite_id,
        ground_station_id=station_id,
        aos_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        los_at=datetime(2024, 1, 1, 10, 10, tzinfo=UTC),
        peak_at=datetime(2024, 1, 1, 10, 5, tzinfo=UTC),
        peak_elevation_deg=42.0,
        track=linestring_to_wkb([(-3.7, 40.4), (-3.6, 40.5)]),
    )

    gs_repo = AsyncMock(spec=GroundStationRepo)
    gs_repo.get_by_id.return_value = object()
    pp_repo = AsyncMock(spec=PassPredictionRepo)
    pp_repo.list_for_ground_station.return_value = [prediction]
    sat_repo = AsyncMock(spec=SatelliteRepo)
    sat_repo.list_all.return_value = [satellite]

    use_case = GetGroundStationPassesUseCase(
        ground_station_repo=gs_repo, pass_prediction_repo=pp_repo, satellite_repo=sat_repo
    )
    views = await use_case.execute(
        ground_station_id=station_id, after=datetime(2024, 1, 1, tzinfo=UTC)
    )

    assert len(views) == 1
    view = views[0]
    assert view.satellite_norad_id == 25544
    assert view.satellite_name == "ISS (ZARYA)"
    assert view.track["type"] == "LineString"
    assert view.track["coordinates"][0] == pytest.approx([-3.7, 40.4])


async def test_get_passes_unknown_station_raises_not_found() -> None:
    gs_repo = AsyncMock(spec=GroundStationRepo)
    gs_repo.get_by_id.return_value = None

    use_case = GetGroundStationPassesUseCase(
        ground_station_repo=gs_repo,
        pass_prediction_repo=AsyncMock(spec=PassPredictionRepo),
        satellite_repo=AsyncMock(spec=SatelliteRepo),
    )
    with pytest.raises(NotFoundError):
        await use_case.execute(
            ground_station_id=uuid.uuid4(), after=datetime(2024, 1, 1, tzinfo=UTC)
        )
