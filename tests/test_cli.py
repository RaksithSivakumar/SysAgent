import unittest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner

from sysagent.cli.commands import app

class TestCLI(unittest.TestCase):

    def setUp(self):
        self.runner = CliRunner()

    @patch("sysagent.cli.commands.run_system_scan")
    @patch("sysagent.cli.commands.save_snapshot")
    def test_cli_scan_text(self, mock_save, mock_scan):
        # Setup mock system scan results
        mock_scan.return_value = {
            "get_os_info": {"hostname": "TestPC", "os_name": "Windows", "uptime_str": "1h"},
            "get_cpu_info": {"model": "CPU Model", "physical_cores": 4, "logical_cores": 8},
            "get_memory_info": {"ram_total_bytes": 8000000000, "ram_used_bytes": 4000000000, "ram_usage_pct": 50.0},
            "get_disk_info": {"partitions": []},
            "get_network_info": {"interfaces": []},
            "get_processes": {"top_cpu": [], "top_memory": []},
            "get_software_info": {},
            "get_security_audit": {},
            "get_firewall_info": {}
        }
        
        result = self.runner.invoke(app, ["scan"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("OS & Host Details", result.stdout)
        self.assertIn("TestPC", result.stdout)

    @patch("sysagent.cli.commands.run_system_scan")
    @patch("sysagent.cli.commands.save_snapshot")
    def test_cli_scan_json_output(self, mock_save, mock_scan):
        mock_scan.return_value = {
            "get_os_info": {"hostname": "TestPC", "os_name": "Windows"}
        }
        result = self.runner.invoke(app, ["scan", "--output", "json"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("TestPC", result.stdout)
        self.assertIn("metadata", result.stdout)

    @patch("sysagent.cli.commands.Config.load")
    @patch("sysagent.cli.commands.get_api_key")
    def test_cli_config_show(self, mock_key, mock_load):
        mock_key.return_value = "fake_key_123"
        mock_conf = MagicMock()
        mock_conf.model = "gemini-2.0-flash"
        mock_conf.read_only_mode = True
        mock_conf.cache_ttl_seconds = 30
        mock_conf.log_level = "INFO"
        mock_conf.max_history_turns = 20
        mock_conf.cpu_usage_pct = 90.0
        mock_conf.memory_usage_pct = 85.0
        mock_conf.disk_usage_pct = 90.0
        mock_conf.battery_pct = 10.0
        mock_load.return_value = mock_conf

        result = self.runner.invoke(app, ["config"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("gemini-2.0-flash", result.stdout)
        self.assertIn("fake_k", result.stdout)

    @patch("sysagent.cli.commands.Config.load")
    @patch("sysagent.cli.commands.set_api_key")
    def test_cli_config_set_api_key(self, mock_set_key, mock_load):
        mock_set_key.return_value = True
        result = self.runner.invoke(app, ["config", "set", "GEMINI_API_KEY", "new_key_value"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("stored securely in keyring", result.stdout)
        mock_set_key.assert_called_with("new_key_value")

    @patch("sysagent.cli.commands.list_snapshots")
    def test_cli_history_list(self, mock_list):
        mock_list.return_value = [
            {"filename": "snapshot_1.json", "path": "/path/snapshot_1.json", "created": "2026-06-07"}
        ]
        result = self.runner.invoke(app, ["history"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("snapshot_1.json", result.stdout)

    @patch("sysagent.cli.commands.Config.load")
    def test_cli_config_set_options(self, mock_load):
        mock_conf = MagicMock()
        mock_load.return_value = mock_conf
        
        # Test alert thresholds and other config set paths
        keys_vals = [
            ("alert.cpu_threshold", "85"),
            ("alert.memory_threshold", "80"),
            ("alert.disk_threshold", "75"),
            ("alert.battery_threshold", "20"),
            ("model", "gemini-1.5-pro"),
            ("read_only_mode", "false"),
            ("cache_ttl_seconds", "15"),
            ("log_level", "DEBUG"),
            ("max_history_turns", "30")
        ]
        for key, val in keys_vals:
            res = self.runner.invoke(app, ["config", "set", key, val])
            self.assertEqual(res.exit_code, 0)
            self.assertIn("updated to", res.stdout)
            mock_conf.save.assert_called()

    @patch("sysagent.cli.commands.run_system_scan")
    @patch("sysagent.cli.commands.encrypt_file")
    @patch("builtins.open")
    def test_cli_report_generation(self, mock_open, mock_encrypt, mock_scan):
        mock_scan.return_value = {}
        
        # Save as normal HTML
        res1 = self.runner.invoke(app, ["report", "--format", "html", "--save", "./test.html"])
        self.assertEqual(res1.exit_code, 0)
        self.assertIn("report written to", res1.stdout)
        mock_open.assert_called()

        # Save encrypted HTML
        res2 = self.runner.invoke(app, ["report", "--format", "json", "--save", "./test.enc", "--encrypt"])
        self.assertEqual(res2.exit_code, 0)
        self.assertIn("encrypted", res2.stdout)
        mock_encrypt.assert_called()

    @patch("sysagent.cli.commands.compare_snapshots")
    @patch("os.path.exists")
    def test_cli_history_diff(self, mock_exists, mock_compare):
        mock_exists.return_value = True
        mock_compare.return_value = {
            "uptime_change_str": "10s",
            "cpu_usage_change_pct": 5.0,
            "ram_usage_change_pct": 0.0,
            "new_exposed_ports": [80],
            "closed_exposed_ports": [],
            "new_processes": ["node"],
            "terminated_processes": []
        }
        res = self.runner.invoke(app, ["history", "diff", "s1.json", "s2.json"])
        self.assertEqual(res.exit_code, 0)
        self.assertIn("Telemetry Diff results", res.stdout)
        self.assertIn("node", res.stdout)

