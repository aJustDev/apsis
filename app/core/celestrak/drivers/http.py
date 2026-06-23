"""Driver HTTP de CelesTrak (fuente de TLEs).

Usa httpx directamente (sin SDK), mapea los codigos de estado a la
jerarquia de errores propia del driver y asume la etiqueta de CelesTrak:
los datos GP se recalculan cada 2h y refrescar antes devuelve 403.
"""

import httpx

from app.core.celestrak.exceptions import (
    CelestrakError,
    RateLimitedError,
    TleNotFound,
    TransientError,
)
from app.core.celestrak.types import TleRecord

_USER_AGENT = "apsis/0.1 (+https://github.com/aJustDev/apsis)"
_NOT_FOUND_BODY = "No GP data found"


class CelestrakHttpClient:
    """Implementacion de `CelestrakClient` sobre httpx."""

    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float = 30.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url
        self._client = http_client or httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        )

    async def fetch_by_catalog_id(self, *, catalog_id: int) -> TleRecord:
        body = await self._get({"CATNR": str(catalog_id), "FORMAT": "TLE"})
        return _parse_records(body)[0]

    async def fetch_group(self, *, group: str) -> list[TleRecord]:
        body = await self._get({"GROUP": group, "FORMAT": "TLE"})
        return _parse_records(body)

    async def close(self) -> None:
        await self._client.aclose()

    async def _get(self, params: dict[str, str]) -> str:
        try:
            response = await self._client.get(self._base_url, params=params)
        except httpx.TimeoutException as exc:
            raise TransientError(f"CelesTrak timeout: {exc}") from exc
        except httpx.TransportError as exc:
            raise TransientError(f"CelesTrak transport error: {exc}") from exc

        text = response.text.strip()
        if response.status_code == 403:
            raise RateLimitedError(text)
        if response.status_code >= 500:
            raise TransientError(f"CelesTrak {response.status_code}")
        if response.status_code == 404 or (response.status_code == 200 and text == _NOT_FOUND_BODY):
            raise TleNotFound(text or "no GP data")
        if response.status_code != 200:
            raise CelestrakError(f"CelesTrak unexpected status {response.status_code}")
        return response.text


def _parse_records(body: str) -> list[TleRecord]:
    text = body.strip()
    if not text or text == _NOT_FOUND_BODY:
        raise TleNotFound(text or "empty response")
    # CelesTrak usa CRLF y el nombre va rellenado a 24 chars: splitlines + strip.
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if len(lines) % 3 != 0:
        raise CelestrakError(f"expected groups of 3 lines, got {len(lines)}")
    records: list[TleRecord] = []
    for index in range(0, len(lines), 3):
        name, line1, line2 = lines[index], lines[index + 1], lines[index + 2]
        if not line1.startswith("1 ") or not line2.startswith("2 "):
            raise CelestrakError(f"malformed TLE record near {name!r}")
        records.append(TleRecord(name=name.strip(), line1=line1, line2=line2))
    return records


__all__ = ["CelestrakHttpClient"]
