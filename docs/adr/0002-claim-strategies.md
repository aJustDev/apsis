# 0002 - Two claim strategies: optimistic UPDATE for jobs, SKIP LOCKED for the outbox

- Status: Accepted
- Date: 2026-06-23

## Context

Both workers may run in several processes/replicas at once and must not process
the same row twice. The jobs table and the outbox table have different shapes:
jobs are a handful of long-lived rows (one per `job_name`), the outbox is a
high-volume stream of short-lived rows.

## Decision

- **Jobs**: claim with an optimistic conditional update,
  `UPDATE scheduled_jobs SET status='RUNNING', lease_until=now()+lease
 WHERE id=:id AND status='PENDING' AND next_run_at<=now() RETURNING ...`.
  Zero rows returned means another worker won the race. A `lease_until` column
  plus a recovery pass (`status='RUNNING' AND lease_until < now() -> PENDING`)
  reclaims jobs orphaned by a crash. Contention is low, so no row locks are
  needed.
- **Outbox**: claim with `SELECT ... WHERE status='PENDING' AND scheduled_at<=now()
 ORDER BY scheduled_at LIMIT 1 FOR UPDATE SKIP LOCKED`, processing exactly one
  event per transaction. The lock is held until that event commits, so other
  workers skip it. Failures bump `retry_count` with exponential backoff and
  jitter into `scheduled_at`, dead-lettering at `max_retries`.

## Consequences

- The lease invariant `JOB_LEASE_SECONDS >= 2 * JOB_HANDLER_TIMEOUT_SECONDS` is
  enforced at startup so a slow-but-alive handler is never reclaimed mid-run.
- One-event-per-transaction is essential for the outbox: batching the select and
  committing inside the loop would release locks on still-pending rows and let a
  second worker double-dispatch them.
- Both paths are at-least-once. Handlers are written to be idempotent:
  `recompute_passes` deletes and reinserts predictions per `(satellite, station)`,
  and TLE ingest upserts by NORAD id. Per-handler state in the outbox row lets a
  retry skip handlers that already succeeded.
