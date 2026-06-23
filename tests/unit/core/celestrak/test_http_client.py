from collections.abc import Callable

import httpx
import pytest

from app.core.celestrak.drivers.http import CelestrakHttpClient
from app.core.celestrak.exceptions import RateLimitedError, TleNotFound, TransientError

ISS_BODY = (
    "ISS (ZARYA)             \r\n"
    "1 25544U 98067A   26173.73662978  .00008151  00000+0  15395-3 0  9997\r\n"
    "2 25544  51.6325 272.6245 0004455 218.9710 141.0958 15.49373286572615\r\n"
)


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> CelestrakHttpClient:
    transport = httpx.MockTransport(handler)
    return CelestrakHttpClient(
        base_url="https://celestrak.org/NORAD/elements/gp.php",
        http_client=httpx.AsyncClient(transport=transport),
    )


async def test_fetch_by_catalog_id_parses_iss() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["CATNR"] == "25544"
        assert request.url.params["FORMAT"] == "TLE"
        return httpx.Response(200, text=ISS_BODY)

    client = _client(handler)
    record = await client.fetch_by_catalog_id(catalog_id=25544)
    assert record.name == "ISS (ZARYA)"
    assert record.line1.startswith("1 25544")
    assert record.line2.startswith("2 25544")
    await client.close()


async def test_fetch_unknown_raises_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="No GP data found")

    client = _client(handler)
    with pytest.raises(TleNotFound):
        await client.fetch_by_catalog_id(catalog_id=999_999_999)
    await client.close()


async def test_rate_limited_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="GP data has not updated since your last download")

    client = _client(handler)
    with pytest.raises(RateLimitedError):
        await client.fetch_group(group="active")
    await client.close()


async def test_fetch_group_parses_multiple_records() -> None:
    body = ISS_BODY + (
        "NOAA 19                 \r\n"
        "1 33591U 09005A   26173.50000000  .00000100  00000+0  10000-3 0  9990\r\n"
        "2 33591  99.0000 200.0000 0013000 100.0000 260.0000 14.13000000 90000\r\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=body)

    client = _client(handler)
    records = await client.fetch_group(group="active")
    assert len(records) == 2
    assert records[1].name == "NOAA 19"
    await client.close()


async def test_server_error_is_transient_even_with_marker_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        # Un 5xx cuyo cuerpo coincide con el marcador not-found debe tratarse
        # como transitorio (reintentable), no como TleNotFound (permanente).
        return httpx.Response(503, text="No GP data found")

    client = _client(handler)
    with pytest.raises(TransientError):
        await client.fetch_group(group="active")
    await client.close()
