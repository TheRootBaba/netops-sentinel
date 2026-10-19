import json
import io
import subprocess
import unittest
from unittest.mock import Mock, patch

from netops_sentinel import monitor


class MonitorTests(unittest.TestCase):
    def test_load_endpoints_returns_validated_ipv4_addresses(self):
        endpoints = monitor.load_endpoints()

        self.assertEqual(len(endpoints), 5)

        for endpoint in endpoints:
            self.assertIn("name", endpoint)
            self.assertIn("ip_address", endpoint)

    @patch("netops_sentinel.monitor.subprocess.run")
    def test_check_endpoint_when_ping_succeeds(self, mock_run):
        mock_run.return_value = Mock(
            returncode=0,
            stdout="Reply from 10.10.10.10",
            stderr="",
        )

        result = monitor.check_endpoint(
            {"name": "PAM-HQ-PC", "ip_address": "10.10.10.10"}
        )

        self.assertEqual(result["status"], "reachable")
        self.assertEqual(result["return_code"], 0)
        self.assertGreaterEqual(result["duration_ms"], 0)
        mock_run.assert_called_once()

    @patch("netops_sentinel.monitor.subprocess.run")
    def test_check_endpoint_when_ping_fails(self, mock_run):
        mock_run.return_value = Mock(
            returncode=1,
            stdout="Request timed out.",
            stderr="",
        )

        result = monitor.check_endpoint(
            {"name": "KELLY-BRANCH-PC", "ip_address": "10.30.10.10"}
        )

        self.assertEqual(result["status"], "unreachable")
        self.assertEqual(result["return_code"], 1)

    @patch("netops_sentinel.monitor.subprocess.run")
    def test_check_endpoint_when_ping_process_times_out(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd="ping", timeout=4
        )

        result = monitor.check_endpoint(
            {"name": "PAM-HQ-PC", "ip_address": "10.10.10.10"}
        )

        self.assertEqual(result["status"], "timeout")
        self.assertIsNone(result["return_code"])

    def test_load_endpoints_rejects_invalid_inventory(self):
        invalid_inventory = json.dumps(
            [
                {
                    "name": "BAD-ENDPOINT",
                    "ip_address": "not-an-ip",
                }
            ]
        )

        with patch.object(monitor, "INVENTORY_FILE") as mock_path:
            mock_path.open.return_value.__enter__.return_value = (
                io.StringIO(invalid_inventory)
            )

            with self.assertRaises(ValueError):
                monitor.load_endpoints()


if __name__ == "__main__":
    unittest.main()
