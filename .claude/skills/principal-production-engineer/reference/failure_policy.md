# Failure Policy: Fail Fast vs Designed Degradation

## Doctrine

Fail fast on broken truth. March on only through designed, bounded, observable degradation. Never silently fallback.

## Failure classes

### Internal invariant violation

Examples:

- impossible enum state;
- negative queue size;
- out-of-bounds index;
- corrupt state;
- NaN in actuator command;
- parser accepted impossible length;
- ownership/lifetime violation;
- control loop missed a hard deadline.

Behavior:

- fail fast;
- fail closed;
- return fatal error;
- trip fault;
- transition to known safe state;
- restart isolated component;
- preserve diagnostics.

Do not continue as if normal.

### Semantic corruption

Examples:

- dataset schema mismatch;
- wrong tokenizer/model pair;
- train/validation leakage;
- invalid labels;
- checkpoint incompatible with model;
- protocol version mismatch that changes semantics.

Behavior:

- fail the operation/job;
- surface clear diagnostics;
- require explicit migration/repair.

### Expected environmental failure

Examples:

- packet loss;
- transient network timeout;
- cache miss;
- one corrupt optional data sample;
- temporary metrics sink outage;
- retryable object storage failure.

Behavior:

- retry/degrade only with explicit budget;
- record structured warning log;
- increment metrics;
- expose degraded status if persistent;
- fail when budget is exceeded.

## Fallback acceptance test

A fallback is allowed only when all are true:

- semantically valid;
- bounded in time/count/error;
- visible via structured log and metric;
- tested;
- does not hide programmer bugs;
- does not silently corrupt state/results;
- has clear operator/user semantics;
- has an alert threshold if production-impacting.

## Logging policy

Warning logs are necessary but insufficient. A fallback should usually emit:

- structured warning log;
- counter/rate metric;
- degraded component status;
- alert threshold if persistent or high rate;
- compact fault code for real-time/safety systems.

Logs must be rate-limited under repeated failure.

## Bad patterns

### Silent fallback

```cpp
if (!load_config(path)) {
    use_default_config();
}
```

### Catch-all march-on

```cpp
try {
    run();
} catch (...) {
    continue;
}
```

### Pretending success

```cpp
if (!send(packet)) {
    return true;
}
```

### Stale data without age budget

```cpp
return last_known_good;
```

## Better patterns

```cpp
auto config = load_config(path);
if (!config) {
    logger.error("Failed to load required config", "path", path, "error", config.error());
    return StartupStatus::FatalConfigError;
}
```

```cpp
auto tuning = load_optional_tuning(path);
if (!tuning) {
    logger.warn("Using conservative tuning defaults", "path", path, "error", tuning.error());
    metrics.increment("config.optional_tuning_fallback");
    tuning = conservative_default_tuning();
}
```

## Domain rule

- Real-time control: never improvise; transition among predesigned states.
- Training pipelines: tolerate bounded infrastructure/sample noise; fail fast on semantic corruption.
- Backend services: degrade optional features; fail closed for auth/security/data integrity.
- Parsers/protocols: invalid input is expected; parse failure is explicit; memory safety is non-negotiable.
