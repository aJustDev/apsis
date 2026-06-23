
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.celestrak.types import TleRecord
from app.core.events import worker as events_worker_module
from app.core.events.bus import EventBus
from app.core.events.models import OutboxEventORM
from app.core.events.worker import OutboxWorker
from app.tracking.event_handlers import recompute_passes as recompute_module
from app.tracking.models import GroundStationORM, PassPredictionORM, SatelliteORM
from app.tracking.repos import GroundStationRepo, SatelliteRepo
from app.tracking.services.geometry import point_to_wkb
from app.tracking.use_cases.ingest_tles import IngestTlesUseCase

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

# TLE de la ISS con epoch ~2026-06-22, para que la ventana de 48h desde "now"
# sea cercana al epoch y SGP4 produzca pasos reales sobre Madrid.
ISS = TleRecord(
    name="ISS (ZARYA)",
    line1="1 25544U 98067A   26173.73662978  .00008151  00000+0  15395-3 0  9997",
    line2="2 25544  51.6325 272.6245 0004455 218.9710 141.0958 15.49373286572615",
)


class _FakeCelestrak:
    async def fetch_group(self, *, group: str) -> list[TleRecord]:
        return [ISS]

    async def fetch_by_catalog_id(self, *, catalog_id: int) -> TleRecord:
        return ISS

    async def close(self) -> None:
        return None


async def _count(factory: async_sessionmaker, model: type) -> int:
    async with factory() as session:
        return (await session.execute(select(func.count()).select_from(model))).scalar_one()


async def test_tle_refresh_to_recompute_passes_end_to_end(
    committing_factory: async_sessionmaker,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Los dos modulos que abren su propia sesion deben usar la factory del test.
    monkeypatch.setattr(events_worker_module, "async_session_factory", committing_factory)
    monkeypatch.setattr(recompute_module, "async_session_factory", committing_factory)

    # 1. Una ground station (Madrid) comprometida en BD.
    async with committing_factory() as session:
        await GroundStationRepo(session).create(
            GroundStationORM(
                name="Madrid",
                location=point_to_wkb(latitude=40.4168, longitude=-3.7038),
                altitude_m=667.0,
            )
        )
        await session.commit()

    # 2. Ingesta de TLEs: upserta el satelite y publica 'tle.refreshed' en el
    #    outbox, en la misma transaccion (outbox transaccional).
    async with committing_factory() as session:
        use_case = IngestTlesUseCase(
            satellite_repo=SatelliteRepo(session),
            celestrak=_FakeCelestrak(),
            event_bus=EventBus(session),
        )
        changed = await use_case.execute(group="active")
        await session.commit()
    assert changed == 1
    assert await _count(committing_factory, SatelliteORM) == 1
    assert await _count(committing_factory, OutboxEventORM) == 1

    # 3. El OutboxWorker reclama el evento y dispara recompute_passes, que
    #    recalcula y persiste los pasos sobre Madrid (skyfield + PostGIS).
    await OutboxWorker()._process_batch()

    async with committing_factory() as session:
        event = (await session.execute(select(OutboxEventORM))).scalar_one()
        assert event.status == "PROCESSED"
        assert event.processed_at is not None

    assert await _count(committing_factory, PassPredictionORM) >= 1
