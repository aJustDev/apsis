import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

from app.tracking.models import GroundStationORM, PassPredictionORM, SatelliteORM
from app.tracking.repos import GroundStationRepo, PassPredictionRepo, SatelliteRepo
from app.tracking.services.geometry import point_to_wkb
from app.tracking.use_cases.compute_passes import ComputePassesUseCase

ISS_LINE1 = "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9000"
ISS_LINE2 = "2 25544  51.6400 208.0000 0006703 130.0000 325.0000 15.50000000    07"


async def test_compute_passes_replaces_and_stores_predictions() -> None:
    satellite_id = uuid.uuid4()
    station_id = uuid.uuid4()
    satellite = SatelliteORM(
        norad_id=25544,
        name="ISS",
        tle_line1=ISS_LINE1,
        tle_line2=ISS_LINE2,
        epoch=datetime(2024, 1, 1, 12, tzinfo=UTC),
    )
    satellite.id = satellite_id
    station = GroundStationORM(
        name="Madrid",
        location=point_to_wkb(latitude=40.4168, longitude=-3.7038),
        altitude_m=667.0,
    )
    station.id = station_id

    sat_repo = AsyncMock(spec=SatelliteRepo)
    sat_repo.get_by_id.return_value = satellite
    gs_repo = AsyncMock(spec=GroundStationRepo)
    gs_repo.get_by_id.return_value = station
    created: list[PassPredictionORM] = []
    pp_repo = AsyncMock(spec=PassPredictionRepo)
    pp_repo.create.side_effect = lambda entity: created.append(entity) or entity

    use_case = ComputePassesUseCase(
        satellite_repo=sat_repo, ground_station_repo=gs_repo, pass_prediction_repo=pp_repo
    )
    start = datetime(2024, 1, 1, tzinfo=UTC)
    count = await use_case.execute(
        satellite_id=satellite_id,
        ground_station_id=station_id,
        window=(start, start + timedelta(days=1)),
    )

    assert count > 0
    assert len(created) == count
    pp_repo.delete_for_satellite_and_station.assert_awaited_once_with(satellite_id, station_id)
    first = created[0]
    assert first.satellite_id == satellite_id
    assert first.ground_station_id == station_id
    assert first.aos_at < first.peak_at < first.los_at
    assert first.peak_elevation_deg >= 10.0
