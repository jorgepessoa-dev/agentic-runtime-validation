from __future__ import annotations

import pathlib
import re
import sys

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLAIM_REQUIRED = {"id", "claim", "source", "criticality", "validation", "status", "evidence"}
CAMPAIGN_REQUIRED = {
    "campaign_id", "target_commit", "validation_repo_commit", "test_version",
    "oracle_version", "environment", "database_version", "worker_count",
    "seed_strategy", "fixed_seeds", "invariants", "failure_condition",
    "sample_count", "started_at",
}


def main() -> int:
    claims = yaml.safe_load((ROOT / "CLAIMS.yaml").read_text())
    if not isinstance(claims, list) or not claims:
        raise SystemExit("CLAIMS.yaml must be a nonempty sequence")
    ids = set()
    for claim in claims:
        if not CLAIM_REQUIRED <= claim.keys():
            raise SystemExit(f"claim missing fields: {claim}")
        if claim["id"] in ids:
            raise SystemExit(f"duplicate claim ID: {claim['id']}")
        ids.add(claim["id"])
    campaigns = list((ROOT / "campaigns").glob("*/CAMPAIGN.yaml"))
    for path in campaigns:
        payload = yaml.safe_load(path.read_text())
        if not CAMPAIGN_REQUIRED <= payload.keys():
            raise SystemExit(f"campaign metadata missing fields: {path}")
        if not re.fullmatch(r"[0-9a-f]{40}", payload["target_commit"]):
            raise SystemExit(f"bad target SHA in {path}")
    print(f"claims={len(claims)} campaign_manifests={len(campaigns)} valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
