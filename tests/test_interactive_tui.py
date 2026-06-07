import unittest
from unittest.mock import patch, MagicMock
from sysagent.cli.interactive import run_repl
from sysagent.cli.tui import make_layout, update_tui_layout, check_quit_key
from sysagent.config import Config

class TestInteractiveTui(unittest.TestCase):

    @patch("sysagent.cli.interactive.Prompt.ask")
    @patch("sysagent.cli.interactive.GeminiAgent")
    def test_repl_exits_immediately(self, mock_agent, mock_prompt):
        mock_prompt.return_value = "exit"
        # run_repl should loop once, see exit, and terminate successfully.
        run_repl()
        mock_prompt.assert_called_once()

    @patch("sysagent.cli.tui.get_cpu_info")
    @patch("sysagent.cli.tui.get_memory_info")
    @patch("sysagent.cli.tui.get_disk_info")
    @patch("sysagent.cli.tui.get_processes")
    @patch("sysagent.cli.tui.get_os_info")
    @patch("sysagent.cli.tui.get_battery_info")
    @patch("sysagent.cli.tui.get_network_info")
    @patch("sysagent.cli.tui.get_firewall_info")
    @patch("sysagent.cli.tui.get_security_audit")
    def test_tui_layout_updates(self, mock_audit, mock_firewall, mock_net, mock_bat, mock_os, mock_proc, mock_disk, mock_mem, mock_cpu):
        # Configure mocked collector return values to prevent KeyError/AttributeError
        mock_cpu.return_value = {"usage_overall_pct": 10.0, "model": "Intel", "physical_cores": 4, "logical_cores": 8, "frequency_current_mhz": 2000}
        mock_mem.return_value = {"ram_usage_pct": 40.0, "ram_total_bytes": 8000000000, "ram_used_bytes": 3200000000, "speed_mhz": "2400", "type": "DDR4"}
        mock_disk.return_value = {"partitions": [{"mountpoint": "/", "usage_pct": 20.0, "total_bytes": 100000000, "fstype": "ext4"}]}
        mock_proc.return_value = {"top_cpu": []}
        mock_os.return_value = {"os_name": "Linux", "os_version": " Ubuntu", "kernel_version": "5.15", "uptime_str": "2h"}
        mock_bat.return_value = {"present": True, "charge_pct": 90.0, "status": "Discharging", "time_remaining_str": "4h"}
        mock_net.return_value = {"interfaces": []}
        mock_firewall.return_value = {"listening_ports": []}
        mock_audit.return_value = {"admin_users": ["root"], "world_writable_files": []}

        config = Config()
        layout = make_layout()
        update_tui_layout(layout, config)

        # Assert panels have been updated
        self.assertIsNotNone(layout["header"])
        self.assertIsNotNone(layout["body"])
        self.assertIsNotNone(layout["footer"])

    @patch("sysagent.cli.tui.get_platform")
    @patch("msvcrt.kbhit", create=True)
    @patch("msvcrt.getch", create=True)
    def test_tui_check_quit_key_windows(self, mock_getch, mock_kbhit, mock_plat):
        mock_plat.return_value = "windows"
        mock_kbhit.return_value = True
        mock_getch.return_value = b"q"
        self.assertTrue(check_quit_key())

        mock_getch.return_value = b"a"
        self.assertFalse(check_quit_key())
