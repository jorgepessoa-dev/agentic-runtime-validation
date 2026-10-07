"""Independent behavioral expectations; intentionally imports no runtime code."""
from __future__ import annotations

from collections.abc import Iterable, Mapping

# For a claim-cap oracle, count durable, unexpired leases whose task and attempt
# epochs agree. This observation is independent of the runtime's task-status SQL.
def bounded_active_descendants(rows: Iterable[Mapping[str, object]], limit: int) -> bool:
    active = {
        str(row["task_id"])
        for row in rows
        if row.get("lease_status") == "ACTIVE"
        and row.get("lease_unexpired") is True
        and row.get("lease_is_current") is True
    }
    return len(active) <= limit


# This transition claim remains ambiguous until the state-machine campaign pins
# the public meaning of terminal versus retryable failure states.
def terminal_state_never_resurrects(terminal_before: bool, terminal_after: bool) -> bool:
    return not terminal_before or terminal_after


def stale_authority_has_no_accepted_effect(accepted: bool, actor_epoch: int, current_epoch: int) -> bool:
    return not (accepted and actor_epoch != current_epoch)


def dependencies_satisfied_before_claim(parent_status: str, dependency: str, has_artifact: bool) -> bool:
    if dependency == "REQUIRES_ACCEPTED":
        return parent_status == "ACCEPTED"
    if dependency == "REQUIRES_ARTIFACT":
        return parent_status in {"RESULT_COMMITTED", "VERIFIED", "ACCEPTED"} and has_artifact
    if dependency == "ORDER_ONLY":
        return parent_status in {"ACCEPTED", "REJECTED", "NEEDS_REVIEW", "FAILED_TRANSIENT",
                                 "FAILED_PERMANENT", "CANCELLED", "QUARANTINED", "BUDGET_EXCEEDED"}
    return False


def plan_claim_lock_isolation(same_plan_blocked: bool, unrelated_plan_blocked: bool) -> bool:
    return same_plan_blocked and not unrelated_plan_blocked


def cancelled_work_has_no_accepted_result(task_status: str, accepted_results: int) -> bool:
    return task_status != "CANCELLED" or accepted_results == 0


def recovered_authority_is_consistent(task_epoch: int, active_lease_epochs: Iterable[int]) -> bool:
    active = tuple(active_lease_epochs)
    return len(active) <= 1 and all(epoch == task_epoch for epoch in active)


def holdout_not_candidate_visible(visible_partitions: Iterable[str]) -> bool:
    return "HOLDOUT" not in set(visible_partitions)


def authority_separated(candidate_can_promote: bool, evaluator_can_promote: bool) -> bool:
    return not candidate_can_promote and not evaluator_can_promote


def tampering_cannot_authorize_promotion(original_digest: str, observed_digest: str,
                                         promoted: bool) -> bool:
    return original_digest == observed_digest or not promoted


def rollback_restores_prior_authority(active_champion: str, prior_champion: str) -> bool:
    return active_champion == prior_champion
