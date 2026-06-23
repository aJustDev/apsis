# 0003 - PostGIS for geospatial state

- Status: Accepted
- Date: 2026-06-23

## Context

Ground stations are points on the Earth. Each predicted pass has a sub-satellite
ground track. A natural query is "which upcoming passes cross this bounding box",
which is a spatial intersection, not something a plain B-tree answers well.

## Decision

Use PostGIS via geoalchemy2:

- `ground_stations.location` is a `POINT` (SRID 4326).
- `pass_predictions.track` is a `LINESTRING` (SRID 4326).
- Both columns carry a GiST spatial index.
- Spatial reads use `ST_MakeEnvelope` + `ST_Intersects`.
- All axis-order handling (PostGIS, GeoJSON and shapely are lon/lat; humans say
  lat/lon) is centralized in `app/tracking/services/geometry.py` so the swap is
  impossible to get wrong elsewhere.

## Consequences

- Real, indexable spatial queries instead of bbox math in Python.
- The database needs the PostGIS extension. The initial migration runs
  `CREATE EXTENSION IF NOT EXISTS postgis`, which requires a role allowed to
  create extensions (superuser, or a pre-provisioned extension).
- Geometry is converted to/from WKB at the persistence boundary and exposed as
  GeoJSON at the API boundary; the rest of the code works with primitives.
