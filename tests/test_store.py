import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.models import AssetRecord, DecisionRecord
from app.store import CanonicalStore


class CanonicalStoreTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = CanonicalStore(Path(self.temp_dir.name) / "store.sqlite3")

    def tearDown(self):
        self.store.close()
        self.temp_dir.cleanup()

    def test_upsert_keeps_one_canonical_row_per_asset_id(self):
        first_record = AssetRecord(
            asset_id="robot-17",
            location="Dock 1",
            status="idle",
            faults=[],
            updated_at="2026-08-16T10:00:00Z",
            source="source_a",
        )
        winning_record = AssetRecord(
            asset_id="robot-17",
            location="Zone C",
            status="idle",
            faults=[],
            updated_at="2026-08-16T10:04:00Z",
            source="source_b",
        )

        self.store.upsert_asset(first_record)
        self.store.upsert_asset(winning_record)

        assets = self.store.list_assets()
        stored_asset = self.store.get_asset("robot-17")

        self.assertEqual(len(assets), 1)
        self.assertIsNotNone(stored_asset)
        self.assertEqual(stored_asset.location, "Zone C")
        self.assertEqual(stored_asset.source, "canonical")

    def test_decision_log_round_trips_structured_evidence(self):
        decision = DecisionRecord(
            decision_id="decision-1",
            asset_id="sensor-22",
            winner="source_b",
            loser="source_a",
            conflict_fields=["status", "faults", "updated_at"],
            rule="recent_fault_safety_override",
            reason="Fault report is recent enough to override normal status.",
            evidence={
                "winner_status": "faulted",
                "winner_faults": ["temperature_spike"],
                "safety_window_minutes": 15,
            },
            created_at=datetime(2026, 8, 16, 10, 5, tzinfo=timezone.utc),
        )

        self.store.record_decision(decision)

        decisions = self.store.list_decisions()

        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0].asset_id, "sensor-22")
        self.assertEqual(decisions[0].rule, "recent_fault_safety_override")
        self.assertEqual(
            decisions[0].evidence["winner_faults"],
            ["temperature_spike"],
        )


if __name__ == "__main__":
    unittest.main()
