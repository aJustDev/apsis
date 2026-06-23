import pytest

from app.tracking.services.geometry import (
    linestring_to_wkb,
    point_to_wkb,
    wkb_to_geojson,
    wkb_to_lonlat,
)

MADRID_LAT, MADRID_LON = 40.4168, -3.7038


def test_point_roundtrip_preserves_lon_lat_order() -> None:
    wkb = point_to_wkb(latitude=MADRID_LAT, longitude=MADRID_LON)
    lon, lat = wkb_to_lonlat(wkb)
    assert lon == pytest.approx(MADRID_LON)
    assert lat == pytest.approx(MADRID_LAT)
    assert lon < 0  # Madrid esta al oeste: es la longitud la negativa, no la latitud


def test_point_geojson_is_lon_first() -> None:
    geojson = wkb_to_geojson(point_to_wkb(latitude=MADRID_LAT, longitude=MADRID_LON))
    assert geojson["type"] == "Point"
    assert geojson["coordinates"] == pytest.approx([MADRID_LON, MADRID_LAT])


def test_linestring_roundtrip_and_geojson() -> None:
    coords = [(-3.7038, 40.4168), (-0.3763, 39.4699), (2.1734, 41.3851)]
    geojson = wkb_to_geojson(linestring_to_wkb(coords))
    assert geojson["type"] == "LineString"
    assert len(geojson["coordinates"]) == 3
    assert geojson["coordinates"][0] == pytest.approx([-3.7038, 40.4168])


def test_linestring_needs_two_points() -> None:
    with pytest.raises(ValueError, match="at least 2 points"):
        linestring_to_wkb([(0.0, 0.0)])
