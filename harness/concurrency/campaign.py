from __future__ import annotations

import contextlib
import datetime as dt
import json
import os
import platform
import random
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any

RUNTIME_SRC = Path(os.environ["AGENTIC_RUNTIME_SRC"]).resolve()
sys.path.insert(0, str(RUNTIME_SRC))

from agentic_runtime.contracts.coordination import PlanNode, PlanVersionProposal  # noqa: E402
from agentic_runtime.coordinator.coordination import CoordinationService  # noqa: E402
from agentic_runtime.coordinator.service import Coordinator  # noqa: E402
from agentic_runtime.persistence.postgres import apply_migrations, connect  # noqa: E402
from oracle.invariants import bounded_active_descendants  # noqa: E402

TARGET = "62f541b64bb616d0cd406b2584162cc38955d74f"
CAMPAIGN_ID = os.environ.get("V1_CAMPAIGN_ID", "V1-CONCURRENCY-001")
BASE_SEED = 20261007001
RACE_COUNTS = 84
CLAIMERS = (2, 10, 50, 100)
SUPPORTED_K = (1, 2, 3)
UNSUPPORTED_K = (5, 20)
ACTIVE_QUERY = """
SELECT t.task_id,t.status AS task_status,l.status AS lease_status,
       (l.lease_until > clock_timestamp()) AS lease_unexpired,
       (l.lease_epoch=t.lease_epoch AND l.lease_epoch=a.lease_epoch) AS lease_is_current,
       a.status AS attempt_status,l.lease_epoch,t.lease_epoch AS task_epoch,a.lease_epoch AS attempt_epoch
FROM runtime.tasks t
LEFT JOIN runtime.leases l ON l.task_id=t.task_id
LEFT JOIN runtime.attempts a
  ON a.task_id=t.task_id AND a.attempt_id=l.attempt_id AND a.lease_epoch=l.lease_epoch
WHERE t.plan_version_id=%s
"""


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


class JitterConnection:
    """Test-only deterministic delays around target calls; runtime source is untouched."""
    def __init__(self, raw: Any, seed: int):
        self.raw = raw
        self.random = random.Random(seed)

    def execute(self, query: str, params: Any = None):
        q = query.lstrip().upper()
        if q.startswith("SELECT T.* FROM RUNTIME.TASKS"):
            time.sleep(self.random.uniform(0, 0.004))
        elif q.startswith("UPDATE RUNTIME.TASKS SET STATUS='LEASED'"):
            time.sleep(self.random.uniform(0, 0.002))
        return self.raw.execute(query, params)

    @contextlib.contextmanager
    def transaction(self):
        time.sleep(self.random.uniform(0, 0.003))
        with self.raw.transaction():
            yield self
            # Hold row/xact locks for a seeded interval before commit.
            time.sleep(self.random.uniform(0, 0.004))

    def __getattr__(self, name: str) -> Any:
        return getattr(self.raw, name)


def snapshot(db: Any, plan_version_id: str) -> list[dict[str, Any]]:
    return db.execute(ACTIVE_QUERY, (plan_version_id,)).fetchall()


def capture_host() -> dict[str, Any]:
    return {
        "captured_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "cpu_count": os.cpu_count(),
        "load_average": os.getloadavg(),
        "memory_kib": {
            line.split(":", 1)[0]: int(line.split()[1])
            for line in Path("/proc/meminfo").read_text().splitlines()
            if line.startswith(("MemTotal:", "MemAvailable:", "SwapTotal:", "SwapFree:"))
        },
    }


def create_workers(db: Any, count: int) -> list[str]:
    coordinator = Coordinator(db)
    workers = [f"v1-worker-{idx:03d}" for idx in range(count)]
    for worker in workers:
        coordinator.register_worker(worker, [])
    return workers


def create_wave(db: Any, wave: int, k: int) -> tuple[str, str]:
    # Separate plans/campaigns keep each race independently attributable.
    task_type = f"v1race{wave:04d}"
    campaign = f"v1campaign{wave:04d}"
    goal = f"v1goal{wave:04d}"
    plan = f"v1plan{wave:04d}"
    version = f"v1version{wave:04d}"
    coordinator = Coordinator(db)
    coordinator.create_campaign(campaign, idempotency_key=f"v1key{wave:04d}",
        description="V1 disposable bounded-claim adversarial race", created_by="v1-harness",
        budget={"max_wall_time_seconds":120}, max_children=6)
    coordinator.create_goal(goal, campaign, description="Disposable V1 race fixture",
        mission_ref=f"v1:{wave:04d}", created_by="v1-harness")
    nodes = tuple(PlanNode(node_key=f"task-{idx}", task_type=task_type,
        objective="Disposable independent claim candidate") for idx in range(7))
    proposal = PlanVersionProposal(plan_id=plan, goal_id=goal, created_by="v1-planner",
        nodes=nodes, estimated_budget={}, max_concurrent_descendants=k)
    plans = CoordinationService(db)
    version_id = plans.propose(version, proposal)
    plans.accept(version_id, accepted_by="v1-independent-policy")
    return version_id, task_type


def run_race(db: Any, workers: list[str], *, n: int, k: int, wave: int,
             seed: int, sample_interval: float) -> dict[str, Any]:
    version_id, task_type = create_wave(db, wave, k)
    barrier = threading.Barrier(n + 1)
    finished = threading.Event()
    sampler_rows: list[dict[str, Any]] = []
    result_lock = threading.Lock()
    outputs: list[dict[str, Any]] = []
    errors: list[str] = []
    sampled = connect(os.environ["V1_DATABASE_URL"])

    def observe() -> None:
        while not finished.is_set():
            rows = snapshot(sampled, version_id)
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            sampler_rows.append({"observed_at": now, "rows": rows,
                "oracle_bounded": bounded_active_descendants(rows, k)})
            if any(not item["oracle_bounded"] for item in sampler_rows[-1:]):
                finished.set()
                return
            time.sleep(sample_interval)

    def claim(worker_idx: int) -> None:
        worker = workers[worker_idx]
        connection = connect(os.environ["V1_DATABASE_URL"])
        jittered = JitterConnection(connection, seed * 1009 + worker_idx)
        try:
            barrier.wait(timeout=20)
            time.sleep(random.Random(seed + worker_idx).uniform(0, 0.003))
            claimed = Coordinator(jittered).claim(worker, lease_seconds=300,
                allowed_task_types=[task_type])
            with result_lock:
                outputs.append({"worker_id": worker, "claimed": None if claimed is None else {
                    key: claimed[key] for key in ("task_id", "attempt_id", "lease_epoch", "worker_id")}})
        except BaseException as exc:  # recorded as harness/runtime error, never swallowed
            with result_lock:
                errors.append(f"{type(exc).__name__}: {exc}")
        finally:
            connection.close()

    sampler = threading.Thread(target=observe, name=f"v1-sampler-{wave}", daemon=True)
    sampler.start()
    threads = [threading.Thread(target=claim, args=(idx,), name=f"v1-claim-{wave}-{idx}")
               for idx in range(n)]
    for thread in threads:
        thread.start()
    barrier.wait(timeout=20)
    for thread in threads:
        thread.join(timeout=60)
    timed_out = [thread.name for thread in threads if thread.is_alive()]
    finished.set()
    sampler.join(timeout=5)
    sampled.close()
    final_rows = snapshot(db, version_id)
    final_ok = bounded_active_descendants(final_rows, k)
    peak = max((sum(1 for row in item["rows"] if row.get("lease_status") == "ACTIVE"
                    and row.get("lease_unexpired") and row.get("lease_is_current"))
                for item in sampler_rows), default=0)
    return {
        "wave": wave, "seed": seed, "plan_version_id": version_id,
        "n_claimers": n, "configured_k": k, "task_type": task_type,
        "claims_returned": sum(item["claimed"] is not None for item in outputs),
        "observations": sampler_rows,
        "observed_peak_active_current_leases": peak,
        "final_active_rows": final_rows,
        "oracle_pass": final_ok and all(item["oracle_bounded"] for item in sampler_rows),
        "errors": errors, "timed_out_threads": timed_out,
        "sample_count": len(sampler_rows),
    }


def main() -> int:
    dsn = os.environ["V1_DATABASE_URL"]
    runtime_head = os.environ.get("V1_RUNTIME_SHA", "")
    if runtime_head != TARGET:
        raise SystemExit(f"target SHA mismatch: expected {TARGET}, got {runtime_head}")
    results_dir = Path(os.environ.get("V1_RESULTS_DIR", "results/V1-CONCURRENCY-001"))
    results_dir.mkdir(parents=True, exist_ok=False)
    admin = connect(dsn); admin.autocommit = True
    applied = apply_migrations(admin)
    migration_count = admin.execute("SELECT count(*) AS n FROM runtime.schema_migrations").fetchone()["n"]
    workers = create_workers(admin, max(CLAIMERS))
    out: dict[str, Any] = {
        "campaign_id": CAMPAIGN_ID, "status": "INCONCLUSIVE",
        "target_commit": TARGET, "runtime_sha_observed": runtime_head,
        "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "environment": capture_host(), "postgres_version": admin.execute("SHOW server_version").fetchone()["server_version"],
        "fresh_migrations_applied_this_run": len(applied), "migration_count": migration_count,
        "seed_strategy": {"base_seed": BASE_SEED, "race_counts_per_supported_cell": RACE_COUNTS},
        "matrix_results": [], "bounded_config_rejections": [], "violations": [], "total_claim_races": 0,
        "limitations": ["Public M10 charter hard-caps max_concurrent_descendants at 3; K=5 and K=20 are rejection probes, not valid race configurations"]
    }
    # Explicitly measure hard-limit behavior for the requested out-of-contract K values.
    from agentic_runtime.contracts.coordination import validate_plan_version
    for k in UNSUPPORTED_K:
        try:
            p = PlanVersionProposal(plan_id=f"v1-limit-probe-{k}", goal_id="v1-probe-goal",
                created_by="v1-probe", nodes=(PlanNode("one", "v1probe", "bound probe"),),
                estimated_budget={}, max_concurrent_descendants=k)
            validate_plan_version(p)
            rejected = False
        except ValueError:
            rejected = True
        out["bounded_config_rejections"].append({
            "k": k, "expected_rejection_from_public_hard_cap_3": k > 3,
            "rejected_by_target": rejected, "oracle_pass": rejected == (k > 3)})
    wave = 0
    stop = False
    jsonl_path = results_dir / "race-observations.jsonl"

    def persist_result() -> None:
        out["updated_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
        out["total_claim_races"] = sum(len(c["results"]) for c in out["matrix_results"])
        tmp = results_dir / "RESULT.json.tmp"
        tmp.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, results_dir / "RESULT.json")

    persist_result()
    for n in CLAIMERS:
        for k in SUPPORTED_K:
            cell = {"n_claimers": n, "k": k, "requested": RACE_COUNTS, "results": []}
            for _ in range(RACE_COUNTS):
                wave += 1
                item = run_race(admin, workers, n=n, k=k, wave=wave,
                    seed=BASE_SEED + wave, sample_interval=0.002)
                compact = {key: value for key, value in item.items()
                           if key not in {"observations", "final_active_rows"}}
                cell["results"].append(compact)
                with jsonl_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(item, sort_keys=True) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                out["total_claim_races"] += 1
                if item["errors"] or item["timed_out_threads"]:
                    out["status"] = "HARNESS_INVALID"
                    out["harness_error"] = {"wave": wave, "errors": item["errors"],
                                              "timed_out_threads": item["timed_out_threads"]}
                    stop = True
                    break
                if not item["oracle_pass"]:
                    out["status"] = "FAIL"
                    out["violations"].append({"wave": wave, "seed": item["seed"],
                        "plan_version_id": item["plan_version_id"], "n_claimers": n, "k": k,
                        "observed_peak": item["observed_peak_active_current_leases"],
                        "final_active_rows": item["final_active_rows"]})
                    stop = True
                    break
            out["matrix_results"].append(cell)
            persist_result()
            # Preserve each cell promptly so a process interruption cannot erase results.
            cell_path = results_dir / f"cell-n{n}-k{k}.json"
            cell_path.write_text(json.dumps(cell, indent=2, sort_keys=True) + "\n")
            if stop:
                break
        if stop:
            break
    if not stop:
        supported_complete = out["total_claim_races"] == len(CLAIMERS)*len(SUPPORTED_K)*RACE_COUNTS
        out["supported_matrix_status"] = "PASS" if supported_complete else "INCONCLUSIVE"
        # The requested K=5/20 races are outside the published hard maximum of 3.
        # They are recorded as rejected inputs, not run under altered limits.
        out["status"] = "INCONCLUSIVE"
        out["incomplete_dimensions"] = ["K=5 and K=20 race legs are outside the public immutable hard cap of 3"]
    out["completed_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    persist_result()
    admin.close()
    print(json.dumps({k: v for k, v in out.items() if k not in {"matrix_results"}}, indent=2, sort_keys=True))
    return 1 if out["status"] in {"FAIL", "HARNESS_INVALID"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
