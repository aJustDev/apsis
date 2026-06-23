from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.tracking.models import GroundStationORM, PassPredictionORM, SatelliteORM
from app.tracking.repos import GroundStationRepo, PassPredictionRepo
from app.tracking.services.geometry import linestring_to_wkb, point_to_wkb, wkb_to_lonlat

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]


async def test_ground_station_point_roundtrip(db_session: AsyncSession) -> None:
    repo = GroundStationRepo(db_session)
    station = await repo.create(
        GroundStationORM(
            name="Madrid",
            location=point_to_wkb(latitude=40.4168, longitude=-3.7038),
            altitude_m=667.0,
        )
    )
    fetched = await repo.get_by_name("Madrid")
    assert fetched is not None
    lon, lat = wkb_to_lonlat(fetched.location)
    assert (lon, lat) == pytest.approx((-3.7038, 40.4168))
    assert fetched.id == station.id


async def test_list_in_bbox_uses_st_intersects(db_session: AsyncSession) -> None:
    station = GroundStationORM(
        name="GS", location=point_to_wkb(latitude=40.4, longitude=-3.7), altitude_m=0.0
    )
    satellite = SatelliteORM(
        norad_id=25544,
        name="ISS",
        tle_line1="1",
        tle_line2="2",
        epoch=datetime(2024, 1, 1, tzinfo=UTC),
    )
    db_session.add_all([station, satellite])
    await db_session.flush()

    base = datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    prediction = PassPredictionORM(
        satellite_id=satellite.id,
        ground_station_id=station.id,
        aos_at=base,
        los_at=base + timedelta(minutes=10),
        peak_at=base + timedelta(minutes=5),
        peak_elevation_deg=42.0,
        track=linestring_to_wkb([(-3.7, 40.4), (-3.6, 40.5), (-3.5, 40.6)]),
    )
    db_session.add(prediction)
    await db_session.flush()

    repo = PassPredictionRepo(db_session)
    hit = await repo.list_in_bbox(min_lon=-4.0, min_lat=40.0, max_lon=-3.0, max_lat=41.0)
    assert [p.id for p in hit] == [prediction.id]

    miss = await repo.list_in_bbox(min_lon=10.0, min_lat=10.0, max_lon=11.0, max_lat=11.0)
    assert miss == []
