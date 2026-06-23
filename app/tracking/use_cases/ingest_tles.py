from dataclasses import dataclass

from app.core.celestrak.driver import CelestrakClient
from app.core.events.bus import EventBus
from app.tracking.models import SatelliteORM
from app.tracking.repos import SatelliteRepo
from app.tracking.services.propagation import tle_epoch, tle_norad_id


@dataclass(slots=True)
class IngestTlesUseCase:
    """Descarga un grupo de TLEs de CelesTrak y upserta los satelites.

    Por cada satelite cuyo TLE cambio publica un evento `tle.refreshed` en el
    outbox (misma transaccion que el upsert -> outbox transaccional); el
    handler recompute_passes recalcula los pasos. Idempotente: si el TLE no
    cambio no actualiza ni publica. No hace commit (lo hace el job worker).
    """

    satellite_repo: SatelliteRepo
    celestrak: CelestrakClient
    event_bus: EventBus

    async def execute(self, *, group: str) -> int:
        records = await self.celestrak.fetch_group(group=group)
        changed = 0
        for record in records:
            norad_id = tle_norad_id(line1=record.line1)
            existing = await self.satellite_repo.get_by_norad_id(norad_id)
            if existing is None:
                satellite = await self.satellite_repo.create(
                    SatelliteORM(
                        norad_id=norad_id,
                        name=record.name,
                        tle_line1=record.line1,
                        tle_line2=record.line2,
                        epoch=tle_epoch(line1=record.line1, line2=record.line2),
                    )
                )
            elif existing.tle_line1 != record.line1 or existing.tle_line2 != record.line2:
                satellite = await self.satellite_repo.update(
                    existing,
                    {
                        "name": record.name,
                        "tle_line1": record.line1,
                        "tle_line2": record.line2,
                        "epoch": tle_epoch(line1=record.line1, line2=record.line2),
                    },
                )
            else:
                continue
            await self.event_bus.publish(
                "tle.refreshed",
                {"satellite_id": str(satellite.id), "norad_id": norad_id},
                aggregate_id=satellite.id,
            )
            changed += 1
        return changed


__all__ = ["IngestTlesUseCase"]
