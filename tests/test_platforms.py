import unittest
from unittest.mock import patch, MagicMock

# Import collectors & utilities under test
from sysagent.collectors.cpu import get_cpu_info
from sysagent.collectors.memory import get_memory_info
from sysagent.collectors.disk import get_disk_info
from sysagent.collectors.gpu import get_gpu_info
from sysagent.collectors.battery import get_battery_info
from sysagent.collectors.os_info import get_os_info
from sysagent.collectors.processes import get_processes
from sysagent.collectors.software import get_software_info
from sysagent.security.firewall import get_firewall_info
from sysagent.security.audit import get_security_audit

class TestPlatforms(unittest.TestCase):

    @patch("sysagent.collectors.memory.get_platform")
    @patch("sysagent.collectors.memory.run_command")
    @patch("sysagent.collectors.memory.is_admin")
    def test_linux_memory_and_specs(self, mock_admin, mock_cmd, mock_plat):
        mock_plat.return_value = "linux"
        mock_admin.return_value = True
        mock_cmd.return_value = ("Speed: 3200 MHz\nType: DDR4", "", 0)
        
        from sysagent.collectors.memory import get_memory_hardware_specs
        specs = get_memory_hardware_specs()
        self.assertEqual(specs["speed_mhz"], "3200 MHz")
        self.assertEqual(specs["type"], "DDR4")

    @patch("sysagent.collectors.gpu.get_platform")
    @patch("sysagent.collectors.gpu.run_command")
    def test_gpu_fallback_platforms(self, mock_cmd, mock_plat):
        # Test Linux fallback (lspci)
        mock_plat.return_value = "linux"
        mock_cmd.return_value = ("00:02.0 VGA compatible controller: Intel Corporation", "", 0)
        info_linux = get_gpu_info()
        self.assertTrue(info_linux["gpu_detected"])
        self.assertEqual(info_linux["gpus"][0]["vendor"], "Intel")

        # Test macOS fallback (system_profiler)
        mock_plat.return_value = "macos"
        mock_cmd.return_value = ("Chipset Model: Apple M2\nVRAM (Total): 8 GB", "", 0)
        info_mac = get_gpu_info()
        self.assertTrue(info_mac["gpu_detected"])
        self.assertEqual(info_mac["gpus"][0]["name"], "Apple M2")

    @patch("sysagent.collectors.battery.get_platform")
    @patch("sysagent.collectors.battery.run_command")
    @patch("os.path.exists")
    @patch("builtins.open")
    def test_battery_fallbacks(self, mock_open, mock_exists, mock_cmd, mock_plat):
        # macOS
        mock_plat.return_value = "macos"
        mock_cmd.return_value = ("Cycle Count: 120", "", 0)
        from sysagent.collectors.battery import get_battery_cycle_count
        self.assertEqual(get_battery_cycle_count(), "120")

        # Linux
        mock_plat.return_value = "linux"
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "150\n"
        mock_open.return_value.__enter__.return_value = mock_file
        self.assertEqual(get_battery_cycle_count(), 150)

    @patch("sysagent.collectors.os_info.get_platform")
    @patch("sysagent.collectors.os_info.run_command")
    @patch("os.path.exists")
    @patch("builtins.open")
    def test_os_info_machine_id_fallbacks(self, mock_open, mock_exists, mock_cmd, mock_plat):
        # Linux
        mock_plat.return_value = "linux"
        mock_exists.return_value = True
        mock_file = MagicMock()
        mock_file.read.return_value = "linux-uuid-123\n"
        mock_open.return_value.__enter__.return_value = mock_file
        from sysagent.collectors.os_info import get_machine_id
        self.assertEqual(get_machine_id(), "linux-uuid-123")

        # macOS
        mock_plat.return_value = "macos"
        mock_cmd.return_value = ('"IOPlatformUUID" = "macos-uuid-456"', "", 0)
        self.assertEqual(get_machine_id(), "macos-uuid-456")

    @patch("sysagent.collectors.processes.get_platform")
    @patch("sysagent.collectors.processes.run_command")
    def test_running_services_fallbacks(self, mock_cmd, mock_plat):
        # Linux (systemd)
        mock_plat.return_value = "linux"
        mock_cmd.return_value = ("nginx.service active running nginx web server", "", 0)
        from sysagent.collectors.processes import get_running_services
        srvs = get_running_services()
        self.assertEqual(len(srvs), 1)
        self.assertEqual(srvs[0]["name"], "nginx")

        # macOS (launchd)
        mock_plat.return_value = "macos"
        mock_cmd.return_value = ("1234 0 com.apple.Finder", "", 0)
        srvs_mac = get_running_services()
        self.assertEqual(len(srvs_mac), 1)
        self.assertEqual(srvs_mac[0]["name"], "com.apple.Finder")

    @patch("sysagent.security.firewall.get_platform")
    @patch("sysagent.security.firewall.run_command")
    def test_firewall_status_fallbacks(self, mock_cmd, mock_plat):
        # Linux
        mock_plat.return_value = "linux"
        mock_cmd.return_value = ("Status: active\nTo Action From\n-- ------ ----", "", 0)
        from sysagent.security.firewall import get_firewall_status
        self.assertEqual(get_firewall_status(), "UFW: Status: active")

        # macOS
        mock_plat.return_value = "macos"
        mock_cmd.return_value = ("1\n", "", 0)
        self.assertEqual(get_firewall_status(), "macOS PF/ALF: Enabled")

    @patch("sysagent.security.audit.get_platform")
    @patch("sysagent.security.audit.run_command")
    def test_security_audit_admin_fallbacks(self, mock_cmd, mock_plat):
        # macOS admin group
        mock_plat.return_value = "macos"
        mock_cmd.return_value = ("GroupMembership: root admin standard", "", 0)
        from sysagent.security.audit import get_admin_users
        admins = get_admin_users()
        self.assertIn("root", admins)
        self.assertIn("admin", admins)
