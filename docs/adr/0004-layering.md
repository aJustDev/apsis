# 0004 - Layered architecture, pure services, drivers behind protocols

- Status: Accepted
- Date: 2026-06-23

## Context

The interesting logic (SGP4 propagation, pass geometry) should be trivial to test
in isolation, and the generic infrastructure (jobs, outbox, db) should be
reusable across domains without knowing about satellites.

## Decision

- Layer each bounded context: `api -> use_cases -> services / repos -> models`.
- **Services are pure**: module-level sync functions, no IO, primitives and
  frozen dataclasses in and out, raising `ValueError` on contract violations.
  CPU-heavy sync work (skyfield/SGP4) is offloaded to a thread by the caller via
  `run_blocking`, never run inline on the event loop.
- **Use cases** are `@dataclass(slots=True)` orchestrators holding repos and
  drivers, with a single `async def execute(...)`; they load data, call the pure
  services, and persist. They raise domain exceptions with stable error codes.
- **External IO lives behind a driver**: `app/core/celestrak/` exposes a
  `Protocol`, an httpx implementation, its own infra error hierarchy, and a
  registry singleton swappable for a fake in tests.
- An **import-linter** contract keeps `app.core` agnostic of `app.tracking`
  (except the two wiring modules) and enforces the layer order.

## Consequences

- Pure services and mocked repos make most tests fast and Docker-free; the driver
  registry lets the outbox pipeline run end-to-end against a fake CelesTrak.
- More files and a little indirection, in exchange for boundaries that are
  checked by a tool rather than by convention.
