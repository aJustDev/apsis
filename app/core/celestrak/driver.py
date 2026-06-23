from typing import Protocol, runtime_checkable

from app.core.celestrak.types import TleRecord


@runtime_checkable
class CelestrakClient(Protocol):
    """Puerto de acceso a la fuente de TLEs (CelesTrak).

    No reintenta ni cachea: el job de ingesta decide la cadencia (CelesTrak
    recalcula los datos GP cada 2h) y la persistencia.
    """

    async def fetch_by_catalog_id(self, *, catalog_id: int) -> TleRecord: ...

    async def fetch_group(self, *, group: str) -> list[TleRecord]: ...
