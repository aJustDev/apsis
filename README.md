# apsis

A satellite pass-prediction backend, built the way I build production services:
**FastAPI + SQLAlchemy 2 (async) + PostGIS**, with **Postgres-native scheduled
jobs and a transactional outbox** instead of a message broker.

Give it a ground station and a satellite, it tells you the next visible passes
and the sub-satellite ground track. Orbital data comes from public
[CelesTrak](https://celestrak.org) TLEs, refreshed on a schedule.

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

## Stack

Python 3.14, FastAPI, SQLAlchemy 2 async, asyncpg, PostGIS (geoalchemy2 +
shapely), skyfield (SGP4 propagation), Alembic. Tooling: uv, ruff, mypy (strict),
import-linter. Tests at two levels: fast unit tests and integration tests on a
real PostGIS via testcontainers.

## Quickstart

```sh
uv sync
docker compose up -d db          # PostGIS on localhost:5432
cp .env.example .env.local       # defaults already match the compose service
uv run alembic upgrade head      # schema + seeds the tle_refresh job
uv run uvicorn app.main:app --reload
```

The job and outbox workers start with the app (FastAPI lifespan). Once the DB is
up, the seeded `tle_refresh` job fetches the CelesTrak `active` group and the
outbox recomputes passes for every registered ground station.

Open `http://localhost:8000/docs` for the API.

## API

| Method | Path                              | Description                                  |
| ------ | --------------------------------- | -------------------------------------------- |
| `GET`  | `/v1/health/liveness`             | Liveness probe                               |
| `GET`  | `/v1/health/readiness`            | Readiness (checks the DB)                    |
| `GET`  | `/v1/satellites`                  | List tracked satellites (paginated)          |
| `POST` | `/v1/ground-stations`             | Register a ground station (lat/lon/altitude) |
| `GET`  | `/v1/ground-stations`             | List ground stations                         |
| `GET`  | `/v1/ground-stations/{id}/passes` | Upcoming passes (GeoJSON ground track)       |

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
