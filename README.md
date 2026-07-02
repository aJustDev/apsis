# apsis

[![CI](https://github.com/aJustDev/apsis/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/aJustDev/apsis/actions/workflows/ci.yml)
[![Python 3.14](https://img.shields.io/badge/python-3.14-3776ab)](pyproject.toml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A satellite pass-prediction backend, built the way I build production services:
**FastAPI + SQLAlchemy 2 (async) + PostGIS**, with **Postgres-native scheduled
jobs and a transactional outbox** instead of a message broker.

Give it a ground station and a satellite, and it returns the next contact
windows: every pass above the station's elevation mask (10 degrees by default)
for the next 48 hours, each with its AOS/LOS times, peak elevation, and the
sub-satellite ground track as GeoJSON. Orbital data comes from public
[CelesTrak](https://celestrak.org) TLEs, refreshed every two hours.

A public instance runs at [apsis.ajustino.dev/docs](https://apsis.ajustino.dev/docs)
and feeds the live pass map at [ajustino.dev](https://ajustino.dev). The design
is written up in the [case study](https://ajustino.dev/case-studies/apsis/).

## Why it exists

It is a reference backend. On a real problem, it shows the architecture and the
trade-offs I reach for:

- **A scheduled job** ingests TLEs every couple of hours: a cron-like worker on a
  single Postgres table, claimed atomically with `UPDATE ... WHERE status='PENDING'
... RETURNING` plus a lease and stale-job recovery. No Celery, no beat.
- **A transactional outbox** publishes domain events in the same transaction as
  the write, so an event exists if and only if the business change committed. A
  worker drains it: woken by `LISTEN/NOTIFY`, claiming one row at a time with
  `FOR UPDATE SKIP LOCKED`, with exponential backoff and per-handler idempotency.
- **PostGIS** stores the ground-station point and each pass ground track as a
  WGS84 `LINESTRING`, and answers spatial questions ("which passes cross this
  bounding box") with a GiST index.
- **Layered by context** (`api -> use_cases -> services -> repos -> models`),
  pure side-effect-free compute services, domain exceptions with stable error
  codes, strict typing, and an import-linter contract that keeps the generic
  core agnostic of the domain.

The point is not the satellites. The point is that queues, jobs, and events on
plain Postgres are enough for a surprising amount of production work, and this is
what that looks like when it is done with care.

## How it works

```
                  every 2h (scheduled_jobs)
  CelesTrak  -->  tle_refresh  -->  upsert satellites  --+
                                                         |  same tx
                            publish "tle.refreshed"  (outbox_events)
                                                         |
                       OutboxWorker  (LISTEN/NOTIFY + SKIP LOCKED)
                                                         |
                            recompute_passes  -->  SGP4 (skyfield)
                                                         |
                        pass_predictions  (PostGIS LINESTRING track)
                                                         |
  GET /v1/ground-stations/{id}/passes  <----------------+   (+ GeoJSON track)
```

A satellite row _is_ the TLE store. `recompute_passes` is idempotent: it deletes
and reinserts the predictions for each `(satellite, ground_station)` pair, so a
retried outbox event converges to the same state.

## Try it against the public instance

```sh
curl -s https://apsis.ajustino.dev/v1/ground-stations
# two ESA stations in Spain: Cebreros and Maspalomas

curl -s "https://apsis.ajustino.dev/v1/ground-stations/870a0d92-8a9b-49a3-8361-8d27f7f9fe3e/passes"
```

Response (abbreviated):

```json
{
  "items": [
    {
      "satellite_norad_id": 25544,
      "satellite_name": "ISS (ZARYA)",
      "aos_at": "2026-07-02T22:24:36.508387Z",
      "los_at": "2026-07-02T22:30:44.193418Z",
      "peak_at": "2026-07-02T22:27:39.733062Z",
      "peak_elevation_deg": 32.86,
      "track": {
        "type": "LineString",
        "coordinates": [[-9.4969, 28.6596], [-8.7278, 29.3906], "..."]
      }
    }
  ],
  "total": 173
}
```

Each track is sampled at 24 points between AOS and LOS, ready to draw on a map.

## Stack

Python 3.14, FastAPI, SQLAlchemy 2 async, asyncpg, PostGIS (geoalchemy2 +
shapely), skyfield (SGP4 propagation), Alembic. Tooling: uv, ruff, mypy (strict),
import-linter. Tests at two levels: fast unit tests and integration tests on a
real PostGIS via testcontainers.

## Quickstart

Requires Python 3.14 (uv fetches it if missing) and Docker for the database.

```sh
uv sync
docker compose up -d db          # PostGIS on localhost:5432
cp .env.example .env.local       # defaults already match the compose service
uv run alembic upgrade head      # schema + seeds the tle_refresh job
uv run uvicorn app.main:app --reload
```

The job and outbox workers start with the app (FastAPI lifespan). A fresh
database has no ground stations, and passes are only computed for registered
stations, so register one right after the app boots:

```sh
curl -s -X POST localhost:8000/v1/ground-stations \
  -H 'content-type: application/json' \
  -d '{"name": "Cebreros", "latitude": 40.4527, "longitude": -4.3676, "altitude_m": 794}'
```

The seeded `tle_refresh` job runs on the first worker poll, upserts the
configured CelesTrak group (`active` by default) and the outbox recomputes
passes for every registered station.

Open `http://localhost:8000/docs` for the API.

## API

| Method | Path                              | Description                                  |
| ------ | --------------------------------- | -------------------------------------------- |
| `GET`  | `/v1/health/liveness`             | Liveness probe                               |
| `GET`  | `/v1/health/readiness`            | Readiness (checks the DB)                    |
| `GET`  | `/v1/satellites`                  | List tracked satellites (paginated)          |
| `POST` | `/v1/ground-stations`             | Register a ground station (lat/lon/altitude) |
| `GET`  | `/v1/ground-stations`             | List ground stations                         |
| `GET`  | `/v1/ground-stations/{id}/passes` | Upcoming contact windows (GeoJSON track)     |

## Layout

```
app/
  core/        config, db, repo/schema bases, exceptions, concurrency
    celestrak/ CelesTrak TLE driver (Protocol + httpx + own errors + registry)
    jobs/      Postgres-native scheduler (model, registry, worker, handlers)
    events/    transactional outbox (model, bus, dispatcher, worker)
    db_registry.py   single import hub: models + handlers
  tracking/    the domain context
    models/ repos/ schemas/   data layer (PostGIS)
    services/  pure compute: geometry, SGP4 propagation, pass computation
    use_cases/ orchestration (register station, compute/list passes, ingest TLEs)
    api/       thin FastAPI routers
    event_handlers/  recompute_passes (outbox consumer)
  api/v1/      router aggregator + health
migrations/    Alembic (async, initial PostGIS migration)
tests/         unit + integration (testcontainers)
```

## Architecture decisions

The load-bearing choices are recorded as ADRs in [`docs/adr/`](docs/adr/):

- [0001: Postgres-native jobs and outbox, no broker](docs/adr/0001-no-broker.md)
- [0002: Two claim strategies: optimistic UPDATE for jobs, SKIP LOCKED for the outbox](docs/adr/0002-claim-strategies.md)
- [0003: PostGIS for geospatial state](docs/adr/0003-postgis.md)
- [0004: Layered architecture, pure services, drivers behind protocols](docs/adr/0004-layering.md)

## Testing and quality gates

```sh
uv run pytest                 # unit tests (fast, no Docker)
uv run pytest -m integration  # integration tests (spins a PostGIS container)
uv run ruff check .
uv run mypy app
uv run lint-imports           # architecture contracts
```

## When a Postgres-only design is the wrong call

- Very high throughput (tens of thousands of claims/sec): table churn and
  `VACUUM` pressure will hurt; reach for a real broker.
- Fan-out to many independent consumers, or streaming / complex routing.
- You are not already running Postgres.

If none of those hold, a table is usually enough.

## License

MIT
