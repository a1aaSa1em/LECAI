import asyncio
import unittest

from app.reconciliation_agent import ReconciliationAgent
from app.sources import get_source_a_assets, get_source_b_assets
from app.store import CanonicalStore


class ReconciliationAgentTest(unittest.TestCase):
    def test_mock_conflict_scenarios_update_canonical_state(self):
        store = CanonicalStore()
        agent = ReconciliationAgent(
            store=store,
            source_a_loader=get_source_a_assets,
            source_b_loader=get_source_b_assets,
        )

        summary = agent.poll_once()
        assets = {asset.asset_id: asset for asset in store.list_assets()}
        decisions = {decision.asset_id: decision for decision in store.list_decisions()}

        self.assertEqual(summary.conflicts_detected, 2)
        self.assertEqual(summary.canonical_updates, 2)
        self.assertEqual(summary.decisions_logged, 2)
        self.assertEqual(set(assets), {"robot-17", "sensor-22"})
        self.assertEqual(len(assets), 2)

        self.assertEqual(assets["robot-17"].location, "Zone C")
        self.assertEqual(assets["robot-17"].source, "canonical")
        self.assertEqual(decisions["robot-17"].winner, "source_b")
        self.assertEqual(decisions["robot-17"].rule, "newest_timestamp")
        self.assertEqual(
            decisions["robot-17"].conflict_fields,
            ["location", "updated_at"],
        )

        self.assertEqual(assets["sensor-22"].status, "faulted")
        self.assertEqual(assets["sensor-22"].faults, ["temperature_spike"])
        self.assertEqual(assets["sensor-22"].source, "canonical")
        self.assertEqual(decisions["sensor-22"].winner, "source_b")
        self.assertEqual(decisions["sensor-22"].rule, "recent_fault_safety_override")
        self.assertEqual(
            decisions["sensor-22"].conflict_fields,
            ["status", "faults", "updated_at"],
        )

    def test_repeated_poll_does_not_duplicate_unchanged_decisions(self):
        store = CanonicalStore()
        agent = ReconciliationAgent(
            store=store,
            source_a_loader=get_source_a_assets,
            source_b_loader=get_source_b_assets,
        )

        first_summary = agent.poll_once()
        second_summary = agent.poll_once()

        self.assertEqual(first_summary.conflicts_detected, 2)
        self.assertEqual(first_summary.canonical_updates, 2)
        self.assertEqual(first_summary.decisions_logged, 2)
        self.assertEqual(second_summary.conflicts_detected, 2)
        self.assertEqual(second_summary.canonical_updates, 0)
        self.assertEqual(second_summary.decisions_logged, 0)
        self.assertEqual(len(store.list_decisions()), 2)


class ReconciliationAgentLoopTest(unittest.IsolatedAsyncioTestCase):
    async def test_background_loop_runs_until_stopped(self):
        store = CanonicalStore()
        agent = ReconciliationAgent(
            store=store,
            source_a_loader=get_source_a_assets,
            source_b_loader=get_source_b_assets,
            poll_interval_seconds=0.01,
        )

        started_status = await agent.start()
        await asyncio.sleep(0.04)
        running_status = agent.status()
        stopped_status = await agent.stop()

        self.assertTrue(started_status.running)
        self.assertGreaterEqual(running_status.polls_completed, 1)
        self.assertFalse(stopped_status.running)
        self.assertIsNone(stopped_status.last_error)
        self.assertEqual(len(store.list_assets()), 2)


if __name__ == "__main__":
    unittest.main()
