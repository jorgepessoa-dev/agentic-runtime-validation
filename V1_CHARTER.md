# V1 Independent Adversarial Validation Charter

## Mission

Try to falsify publicly stated Agentic Runtime invariants using independent, reproducible observations. A confirmed failure is valuable evidence. V1 is not a feature program, refactor, marketing exercise, or attempt to obtain PASS.

## Frozen target

- Public repository: `jorgepessoa-dev/agentic-runtime`
- Runtime commit: `62f541b64bb616d0cd406b2584162cc38955d74f`
- Public branch at freeze: `main`
- Runtime source, migrations, thresholds, state semantics, claim query, concurrency, fencing, leases, retry/cancel, holdout, promotion, rollback are immutable during any campaign.

A campaign targets only this exact SHA. A later runtime commit requires a new campaign identity and cannot replace prior results.

## Independence rules

1. Oracle rules are handwritten from public behavioral claims and this charter, not imported from runtime constants, state definitions, transition helpers, or query results.
2. Runtime APIs may be exercised as the system under test. Durable PostgreSQL state, locks, process state, and outputs are observed independently.
3. Internal acceptance labels and tests are context only, never proof.
4. Ambiguous public language is recorded as `AMBIGUOUS`; no interpretation is invented.
5. Campaign metadata is frozen and committed before its first operation. Results are separate, append-only artifacts.

## Campaign lifecycle

Each campaign has immutable `CAMPAIGN.yaml` with target SHA, harness/oracle versions, environment, fixed seed strategy, invariants, and failure conditions. Results use exactly `PASS`, `FAIL`, `INCONCLUSIVE`, or `HARNESS_INVALID`. Harness corrections preserve the old version and invalidate/restart affected campaigns. Runtime fixes occur only in a separate post-campaign phase.

On a failure: stop that campaign, preserve seeds, raw logs, database snapshot where safe, and a minimal reproducer. Do not retry to turn failure into PASS. Classify confirmed findings CRITICAL/HIGH/MEDIUM/LOW/HARNESS. Security-sensitive findings stay private until handled safely.

## Independent concurrency oracle

For each accepted plan version p and each observation time t:

`count(distinct task_id where task.plan_version_id=p and task.status is execution-active and there is a matching unexpired ACTIVE lease for current task epoch) <= configured max_concurrent_descendants(p)`.

The execution-active status set is written independently in `oracle/invariants.py`; it is not imported from the runtime. Lease/task/attempt authority is checked by direct SQL joins. Counts are sampled while workers are concurrently claiming, not only after the race.

A claim race is one synchronized fan-out wave of N independent claim transactions against one plan's dispatchable tasks, plus a high-frequency durable-state sampler during the wave. Every claim result and final active-row set is retained.

## Safety and scope

All databases and workers are disposable and local. No production endpoint, credentials, provider, or remote worker is used. V1 is not M11 and adds no runtime feature. No benchmark comparison to other products is part of this gate.

## Exit status

V1 is accepted only after planned campaigns and reproduction gates are either executed or explicitly listed as incomplete, raw results are preserved, claim coverage is classified, unresolved CRITICAL/HIGH findings are stated, and runtime SHA is verified unchanged. Valid outcomes include `ACCEPTED — NO CRITICAL VIOLATIONS FOUND`, `ACCEPTED — VIOLATIONS FOUND`, or `INCOMPLETE`.
