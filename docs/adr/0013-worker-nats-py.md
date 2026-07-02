# ADR-0013: Worker consumes NATS with nats-py directly

- Status: Accepted
- Date: 2026-07-02

## Context

Milestone 1 required the first event consumers (parse and normalize). ADR-0004 left the consumer framework open between using `nats-py` directly and adopting FastStream.

## Decision

Use `nats-py` directly behind the small `EventBus` wrapper in `shared/events.py`. Handlers are plain async functions receiving a session, the bus, and a scan id. Delivery policy is explicit in `platform/worker.py`: manual ack on success, `nak` with a 10 s delay on failure, give up (ack + error log) after 5 deliveries, and malformed messages are acked immediately since they can never succeed.

## Consequences

- Positive: two fewer layers between a message and its handler; retry behavior is visible in twenty lines of code instead of framework configuration; one less dependency to track.
- Negative: no declarative router, middleware, or built-in test client; each subscription is wired by hand.
- Revisit: if the consumer count grows past roughly a dozen or cross-cutting middleware (tracing, DLQs, schema registry) accumulates, reevaluate FastStream in Milestone 3+ with a migration path through the existing `EventBus` seam.
