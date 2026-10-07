# Environment and clean setup

## Required

- Linux x86_64; Python 3.13; PostgreSQL 16+; `uv`; git.
- No provider credentials or external services.
- Work only in a disposable database with local loopback binding.

## Runtime pin

```sh
git clone https://github.com/jorgepessoa-dev/agentic-runtime.git runtime
git -C runtime checkout 62f541b64bb616d0cd406b2584162cc38955d74f
```

Verify `git -C runtime rev-parse HEAD` equals the pin before any run.

## Temporary storage

Use disk-backed temporary storage, not `/tmp` when it is a small tmpfs:

```sh
export V1_ROOT="$PWD/.v1-work"
mkdir -p "$V1_ROOT/tmp"
export TMPDIR="$V1_ROOT/tmp"
```

Initialize and stop a disposable PostgreSQL cluster per campaign. Never connect to a non-disposable database. Campaign result records must include PostgreSQL version, OS/kernel, CPU/memory, worker count, and exact command.

## State

`CAMPAIGN.yaml` is committed before the first operation. Store raw campaign output in a new results directory; never overwrite prior results. Campaign status is one of PASS, FAIL, INCONCLUSIVE, HARNESS_INVALID.
