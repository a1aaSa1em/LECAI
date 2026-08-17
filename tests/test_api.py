import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.reconciliation_agent import ReconciliationAgent
from app.sources import get_source_a_assets, get_source_b_assets
from app.store import CanonicalStore


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = CanonicalStore(Path(self.temp_dir.name) / "api.sqlite3")
        self.agent = ReconciliationAgent(
            store=self.store,
            source_a_loader=get_source_a_assets,
            source_b_loader=get_source_b_assets,
            poll_interval_seconds=60,
        )
        self.app = create_app(self.agent, self.store, auto_start=False)

    def tearDown(self):
        if self.agent.is_running:
            with TestClient(self.app) as client:
                client.post("/agent/stop")
        self.store.close()
        self.temp_dir.cleanup()

    def test_api_exposes_sources_decisions_and_canonical_state(self):
        with TestClient(self.app) as client:
            self.assertEqual(client.get("/health").json(), {"status": "ok"})
            self.assertEqual(len(client.get("/source-a/assets").json()), 2)
            self.assertEqual(len(client.get("/source-b/assets").json()), 2)

            poll_summary = client.post("/agent/poll-once").json()
            self.assertEqual(poll_summary["conflicts_detected"], 2)
            self.assertEqual(poll_summary["canonical_updates"], 2)
            self.assertEqual(poll_summary["decisions_logged"], 2)

            assets = {
                asset["asset_id"]: asset for asset in client.get("/assets").json()
            }
            self.assertEqual(set(assets), {"robot-17", "sensor-22"})
            self.assertEqual(assets["robot-17"]["location"], "Zone C")
            self.assertEqual(assets["sensor-22"]["status"], "faulted")

            robot = client.get("/assets/robot-17").json()
            self.assertEqual(robot["source"], "canonical")
            self.assertEqual(robot["location"], "Zone C")

            decisions = {
                decision["asset_id"]: decision
                for decision in client.get("/decisions").json()
            }
            self.assertEqual(decisions["robot-17"]["rule"], "newest_timestamp")
            self.assertEqual(
                decisions["sensor-22"]["rule"],
                "recent_fault_safety_override",
            )

            missing = client.get("/assets/does-not-exist")
            self.assertEqual(missing.status_code, 404)

    def test_agent_start_stop_status_endpoints(self):
        with TestClient(self.app) as client:
            initial_status = client.get("/agent/status").json()
            self.assertFalse(initial_status["running"])

            started_status = client.post("/agent/start").json()
            self.assertTrue(started_status["running"])

            running_status = client.get("/agent/status").json()
            self.assertTrue(running_status["running"])

            stopped_status = client.post("/agent/stop").json()
            self.assertFalse(stopped_status["running"])


if __name__ == "__main__":
    unittest.main()
