"""Servicio puro de conversion geometrica (WGS84 / PostGIS).

Sin side-effects, sin IO. Centraliza el orden de ejes: shapely, GeoJSON y
PostGIS guardan (lon, lat), pero las personas dicen (lat, lon). Toda
conversion entre coordenadas y geometrias WKB pasa por aqui para que el
swap sea imposible de equivocar fuera de este modulo.
"""

from collections.abc import Sequence
from typing import Any

from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import LineString, Point, mapping

SRID_WGS84 = 4326


def point_to_wkb(*, latitude: float, longitude: float) -> WKBElement:
    return from_shape(Point(longitude, latitude), srid=SRID_WGS84)


def linestring_to_wkb(points: Sequence[tuple[float, float]]) -> WKBElement:
    """`points` en orden (lon, lat). Una LINESTRING necesita >= 2 puntos."""
    if len(points) < 2:
        raise ValueError("a linestring needs at least 2 points")
    return from_shape(LineString(list(points)), srid=SRID_WGS84)


def wkb_to_lonlat(element: WKBElement) -> tuple[float, float]:
    point = to_shape(element)
    return (float(point.x), float(point.y))


def wkb_to_geojson(element: WKBElement) -> dict[str, Any]:
    # mapping() devuelve tuplas en 'coordinates'; las normalizamos a listas
    # para un JSON/Pydantic limpio.
    geometry: dict[str, Any] = dict(mapping(to_shape(element)))
    geometry["coordinates"] = _to_lists(geometry["coordinates"])
    return geometry


def _to_lists(coordinates: Any) -> Any:
    if isinstance(coordinates, list | tuple):
        return [_to_lists(item) for item in coordinates]
    return coordinates


__all__ = [
    "SRID_WGS84",
    "linestring_to_wkb",
    "point_to_wkb",
    "wkb_to_geojson",
    "wkb_to_lonlat",
]
