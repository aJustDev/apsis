import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from app.core.celestrak.driver import CelestrakClient
from app.core.celestrak.types import TleRecord
from app.core.events.bus import EventBus
from app.tracking.models import SatelliteORM
from app.tracking.repos import SatelliteRepo
from app.tracking.use_cases.ingest_tles import IngestTlesUseCase

ISS = TleRecord(
    name="ISS (ZARYA)",
    line1="1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9000",
    line2="2 25544  51.6400 208.0000 0006703 130.0000 325.0000 15.50000000    07",
)


async def test_ingest_creates_new_satellite_and_publishes() -> None:
    celestrak = AsyncMock(spec=CelestrakClient)
    celestrak.fetch_group.return_value = [ISS]
    repo = AsyncMock(spec=SatelliteRepo)
    repo.get_by_norad_id.return_value = None

    def _create(entity: SatelliteORM) -> SatelliteORM:
        entity.id = uuid.uuid4()
        return entity

    repo.create.side_effect = _create
    bus = AsyncMock(spec=EventBus)

    use_case = IngestTlesUseCase(satellite_repo=repo, celestrak=celestrak, event_bus=bus)
    changed = await use_case.execute(group="active")

    assert changed == 1
    created = repo.create.await_args.args[0]
    assert created.norad_id == 25544
    bus.publish.assert_awaited_once()


async def test_ingest_skips_unchanged_satellite() -> None:
    celestrak = AsyncMock(spec=CelestrakClient)
    celestrak.fetch_group.return_value = [ISS]
    existing = SatelliteORM(
        norad_id=25544,
        name="ISS",
        tle_line1=ISS.line1,
        tle_line2=ISS.line2,
        epoch=datetime(2024, 1, 1, tzinfo=UTC),
    )
    repo = AsyncMock(spec=SatelliteRepo)
    repo.get_by_norad_id.return_value = existing
    bus = AsyncMock(spec=EventBus)

    use_case = IngestTlesUseCase(satellite_repo=repo, celestrak=celestrak, event_bus=bus)
    changed = await use_case.execute(group="active")

    assert changed == 0
    repo.update.assert_not_awaited()
    bus.publish.assert_not_awaited()


async def test_ingest_updates_changed_tle_and_publishes() -> None:
    celestrak = AsyncMock(spec=CelestrakClient)
    celestrak.fetch_group.return_value = [ISS]
    existing = SatelliteORM(
        norad_id=25544,
        name="old",
        tle_line1="1 old",
        tle_line2="2 old",
        epoch=datetime(2024, 1, 1, tzinfo=UTC),
    )
    existing.id = uuid.uuid4()
    repo = AsyncMock(spec=SatelliteRepo)
    repo.get_by_norad_id.return_value = existing
    repo.update.side_effect = lambda entity, data: entity
    bus = AsyncMock(spec=EventBus)

    use_case = IngestTlesUseCase(satellite_repo=repo, celestrak=celestrak, event_bus=bus)
    changed = await use_case.execute(group="active")

    assert changed == 1
    repo.update.assert_awaited_once()
    bus.publish.assert_awaited_once()
