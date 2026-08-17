import unittest

from app.conflict_policy import resolve_conflict
from app.models import AssetRecord


def make_asset(**overrides):
    fields = {
        "asset_id": "robot-17",
        "location": "Zone A",
        "status": "operational",
        "faults": [],
        "updated_at": "2026-08-16T10:00:00Z",
        "source": "source_a",
    }
    fields.update(overrides)
    return AssetRecord(**fields)


class ConflictPolicyTest(unittest.TestCase):
    def test_recent_fault_report_wins_over_newer_normal_status(self):
        source_a = make_asset(
            status="operational",
            updated_at="2026-08-16T10:10:00Z",
            source="source_a",
        )
        source_b = make_asset(
            status="faulted",
            faults=["motor_overheat"],
            updated_at="2026-08-16T10:05:00Z",
            source="source_b",
        )

        decision = resolve_conflict(source_a, source_b)

        self.assertIsNotNone(decision)
        self.assertEqual(decision.winner.source, "source_b")
        self.assertEqual(decision.rule, "recent_fault_safety_override")
        self.assertIn("status", decision.conflict_fields)

    def test_newer_timestamp_wins_when_no_safety_override_applies(self):
        source_a = make_asset(
            location="Zone A",
            updated_at="2026-08-16T10:00:00Z",
            source="source_a",
        )
        source_b = make_asset(
            location="Zone C",
            updated_at="2026-08-16T10:04:00Z",
            source="source_b",
        )

        decision = resolve_conflict(source_a, source_b)

        self.assertIsNotNone(decision)
        self.assertEqual(decision.winner.source, "source_b")
        self.assertEqual(decision.rule, "newest_timestamp")
        self.assertEqual(decision.conflict_fields, ["location", "updated_at"])

    def test_source_reliability_breaks_timestamp_tie(self):
        source_a = make_asset(
            location="Zone A",
            updated_at="2026-08-16T10:00:00Z",
            source="source_a",
        )
        source_b = make_asset(
            location="Zone C",
            updated_at="2026-08-16T10:00:00Z",
            source="source_b",
        )

        decision = resolve_conflict(source_a, source_b)

        self.assertIsNotNone(decision)
        self.assertEqual(decision.winner.source, "source_a")
        self.assertEqual(decision.rule, "source_reliability_tiebreaker")


if __name__ == "__main__":
    unittest.main()
