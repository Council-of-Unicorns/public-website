# Domain-Specific Production Policies

## Real-time control / robotics

Doctrine: never improvise in hard real-time or safety-critical paths. Transition among predesigned states.

Require:

- no dynamic allocation in the control loop;
- no exceptions in the control loop;
- no unbounded locks or blocking I/O;
- bounded execution time;
- finite, range-checked actuator commands;
- watchdog/deadline behavior;
- compact fault reporting;
- safe-state transitions;
- observability outside the hard RT path.

Fail fast/safe-state on:

- NaN/Inf state or command;
- stale sensor data beyond budget;
- missed hard deadline;
- invalid joint limit/state estimate;
- impossible mode transition;
- memory corruption suspicion.

## Networking / parsers / protocols

Doctrine: invalid input is expected; memory unsafety is never acceptable.

Require:

- bounds-checked parsing;
- explicit parse errors;
- no unchecked casts over wire data;
- endian/alignment handling;
- fuzz tests for parsers;
- golden tests for compatibility;
- no unbounded per-peer memory growth;
- backpressure and load shedding;
- clear protocol version handling;
- security fail-closed behavior.

## Training / data pipelines

Doctrine: tolerate bounded infrastructure and sample-level noise, but fail fast on semantic corruption.

Continue with budget for:

- transient object-store read errors;
- isolated corrupt samples;
- dataloader worker restarts;
- optional logging sink outages.

Fail fast on:

- schema mismatch;
- label corruption;
- train/validation leakage;
- NaN loss beyond recovery policy;
- incompatible checkpoint/model/tokenizer;
- too many corrupt samples;
- silent truncation;
- missing required shard.

Require:

- sample-failure budget;
- dataset integrity checks;
- reproducibility metadata;
- checkpointing;
- validation gates;
- metrics and alerts for skipped data.

## Backend services

Doctrine: degrade optional behavior, fail closed for integrity/security.

Require:

- explicit timeouts;
- bounded retries with backoff/jitter;
- circuit breakers where appropriate;
- idempotency for retries;
- structured logs and metrics;
- backpressure;
- graceful shutdown;
- clear ownership of background tasks;
- no hidden network calls behind innocent getters.

Fail closed on:

- auth/permission ambiguity;
- data-integrity uncertainty;
- payment/security-critical errors;
- migration/schema mismatch.
