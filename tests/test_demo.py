import io
import unittest
from contextlib import redirect_stdout

from demo import run_demo


class DemoTest(unittest.TestCase):
    def test_demo_prints_conflicts_decisions_and_canonical_state(self):
        output = io.StringIO()

        with redirect_stdout(output):
            exit_code = run_demo()

        text = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Conflict Decisions", text)
        self.assertIn("robot-17", text)
        self.assertIn("newest_timestamp", text)
        self.assertIn("sensor-22", text)
        self.assertIn("recent_fault_safety_override", text)
        self.assertIn("Canonical State", text)
        self.assertIn("location=Zone C", text)
        self.assertIn("status=faulted", text)
        self.assertIn("new decisions logged: 0", text)


if __name__ == "__main__":
    unittest.main()
