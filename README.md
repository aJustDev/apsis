# apsis

A satellite pass-prediction backend, built the way I build production services:
**FastAPI + SQLAlchemy 2 (async) + PostGIS**, with **Postgres-native scheduled
jobs and a transactional outbox** instead of a message broker.

Give it a location and a satellite, it tells you the next visible passes and the
ground track. Orbital data comes from public [CelesTrak](https://celestrak.org)
TLEs, refreshed on a schedule.

## Why it exists

It is a reference backend. It shows, on a real problem, the architecture and the
trade-offs I reach for:

- **A scheduled job** ingests TLEs every couple of hours - a cron-like worker
  built on a single Postgres table (`SELECT ... FOR UPDATE` claim + lease,
  stale-job recovery), no Celery, no beat.
- **A transactional outbox** publishes domain events in the same transaction as
  the write, then a worker drains them via `LISTEN/NOTIFY` + `FOR UPDATE SKIP
LOCKED`. Exactly-once-ish delivery without a broker.
- **PostGIS** holds the ground tracks and answers "what is overhead right now".
- **Layered** by context (`api -> use_cases -> services -> repos -> models`),
  domain exceptions with stable error codes, strict typing.

The point is not the satellites. The point is that queues, jobs, and events on
plain Postgres are enough for a surprising amount of production work - and this
is what that looks like when it is done with care.

## Stack

Python 3.14, FastAPI, SQLAlchemy 2 async, asyncpg, PostGIS, Alembic, skyfield
(SGP4 propagation). uv, ruff, mypy, import-linter. Tests at three levels (unit,
functional, integration on real Postgres via testcontainers).

## When a Postgres-only design is the wrong call

- Very high throughput (tens of thousands of claims/sec): the table churn and
  `VACUUM` pressure will hurt; reach for a real broker.
- Fan-out to many independent consumers, or streaming / complex routing.
- You are not already running Postgres.

If none of those hold, a table is usually enough.

## Status

`v0.1` - in progress.

## License

MIT
