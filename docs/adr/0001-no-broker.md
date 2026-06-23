# 0001 - Postgres-native jobs and outbox, no broker

- Status: Accepted
- Date: 2026-06-23

## Context

apsis needs two kinds of background work: recurring tasks (refresh TLEs from
CelesTrak every couple of hours) and reliable, decoupled side effects (recompute
passes when a satellite's TLE changes). The reflex answer is a broker plus a
worker framework (Celery + RabbitMQ/Redis, or similar). apsis already runs
Postgres and has no other infrastructure.

## Decision

Build both on Postgres:

- A `scheduled_jobs` table plus an in-process `JobWorker` for cron-like work.
- A transactional outbox (`outbox_events`) plus an `OutboxWorker` for domain
  events, where the event is written in the same transaction as the business
  change.

No external broker, no separate beat scheduler.

## Consequences

- One fewer moving part to deploy, monitor and reason about; everything is
  inspectable with SQL.
- Events are atomic with the write that caused them: an event exists if and only
  if its transaction committed.
- Throughput is bounded by table churn and `VACUUM` pressure. This is fine for
  apsis-scale work and wrong for tens of thousands of claims per second.
- Delivery is at-least-once, so handlers must be idempotent (see
  [0002](0002-claim-strategies.md)).
