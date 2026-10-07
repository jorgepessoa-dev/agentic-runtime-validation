# Agentic Runtime Independent Validation (V1)

This repository is an independent adversarial harness for the public Agentic Runtime invariants. It does not modify or import expected values from the runtime implementation. Runtime execution adapters may invoke the separately pinned runtime source; oracle rules are separately written from the published contract.

## Frozen target

- Repository: `jorgepessoa-dev/agentic-runtime`
- Commit: `62f541b64bb616d0cd406b2584162cc38955d74f`
- Branch at freeze: `main`

A result is only attributed to this target when the checked-out runtime SHA matches exactly.

## Status

V1 is in progress. No PASS label is assigned before campaign evidence exists. See `V1_CHARTER.md`, `CLAIMS.yaml`, `campaigns/`, and `results/`.

## First campaign: bounded descendant claiming

The first campaign manifest will be committed before the first campaign operation. Until then, no campaign has started. The planned matrix covers supported configured limits only; the public M10 contract hard-caps the limit at three, so requests for five and twenty are input-rejection probes rather than valid configurations. All runs use a disposable PostgreSQL database and direct durable-state observations. No external provider is used.

## Reproduction

The harness setup and exact command are recorded in `ENVIRONMENT.md` and the campaign manifest once frozen. A third party must clone this repository and the exact runtime SHA independently.
