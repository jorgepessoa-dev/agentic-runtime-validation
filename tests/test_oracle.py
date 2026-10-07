from __future__ import annotations

import unittest

from oracle.invariants import bounded_active_descendants


class BoundedLeaseOracleTests(unittest.TestCase):
    def test_counts_distinct_current_unexpired_active_leases(self) -> None:
        rows = [
            {"task_id": "a", "lease_status": "ACTIVE", "lease_unexpired": True, "lease_is_current": True},
            {"task_id": "b", "lease_status": "ACTIVE", "lease_unexpired": True, "lease_is_current": True},
            # A stale epoch, expired lease, or released lease is not current authority.
            {"task_id": "c", "lease_status": "ACTIVE", "lease_unexpired": True, "lease_is_current": False},
            {"task_id": "d", "lease_status": "ACTIVE", "lease_unexpired": False, "lease_is_current": True},
            {"task_id": "e", "lease_status": "RELEASED", "lease_unexpired": True, "lease_is_current": True},
        ]
        self.assertTrue(bounded_active_descendants(rows, 2))
        self.assertFalse(bounded_active_descendants(rows, 1))

    def test_duplicate_rows_for_one_task_do_not_inflate_authority_count(self) -> None:
        row = {"task_id": "a", "lease_status": "ACTIVE", "lease_unexpired": True, "lease_is_current": True}
        self.assertTrue(bounded_active_descendants([row, row], 1))

    def test_missing_lease_authority_does_not_count(self) -> None:
        self.assertTrue(bounded_active_descendants([{"task_id": "a", "lease_status": None}], 0))


if __name__ == "__main__":
    unittest.main()
