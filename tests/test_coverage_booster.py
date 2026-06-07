import os
import unittest
import psutil
from unittest.mock import patch, MagicMock

# Import targets
from sysagent.collectors.network import get_network_info
from sysagent.collectors.disk import get_disk_info
from sysagent.collectors.software import get_software_info
from sysagent.security.firewall import get_firewall_info
from sysagent.security.audit import get_security_audit

class TestCoverageBooster(unittest.TestCase):

    @patch("psutil.net_connections")
    @patch("psutil.Process")
    def test_network_access_denied_handling(self, mock_proc, mock_conns):
        # Trigger psutil.AccessDenied inside net_connections call
        mock_conns.side_effect = psutil.AccessDenied()
        
        # Mock connection fallback for current process
        c = MagicMock()
        c.laddr = MagicMock(ip="127.0.0.1", port=5000)
        c.raddr = MagicMock(ip="127.0.0.1", port=80)
        c.fd = 10
        c.family = 2
        c.type = 1
        c.status = "ESTABLISHED"
        
        mock_proc.return_value.connections.return_value = [c]
        
        res = get_network_info()
        self.assertTrue(len(res["connections"]) > 0)
        self.assertEqual(res["connections"][0]["local_address"], "127.0.0.1:5000")

    @patch("psutil.net_connections")
    @patch("psutil.Process")
    def test_firewall_connections_fallback(self, mock_proc, mock_conns):
        # Mock network socket reading exceptions
        mock_conns.side_effect = Exception("Socket read error")
        
        # Mock connections fallback for current process
        c = MagicMock()
        c.status = "LISTEN"
        c.laddr = MagicMock(ip="0.0.0.0", port=8080)
        c.raddr = None
        c.type = 1
        mock_proc.return_value.connections.return_value = [c]
        
        info = get_firewall_info()
        self.assertTrue(len(info["listening_ports"]) > 0)
        self.assertEqual(info["listening_ports"][0]["port"], 8080)

    @patch("shutil.which")
    @patch("sysagent.collectors.software.run_command")
    def test_software_docker_containers(self, mock_cmd, mock_which):
        mock_which.side_effect = lambda x: "/usr/bin/docker" if "docker" in x else None
        # Return version info, daemon status, and running containers list sequentially
        mock_cmd.side_effect = [
            ("Docker version 20.10.7", "", 0),
            ("Docker Info details", "", 0),
            ("c123|web-app|running|nginx:alpine", "", 0)
        ]
        res = get_software_info()
        self.assertTrue(res["docker"]["installed"])
        self.assertTrue(res["docker"]["running"])
        self.assertEqual(len(res["docker"]["containers"]), 1)
        self.assertEqual(res["docker"]["containers"][0]["name"], "web-app")

    @patch("importlib.metadata.distributions")
    def test_software_pip_packages_count(self, mock_dists):
        m_dist = MagicMock()
        m_dist.metadata = {"Name": "requests"}
        mock_dists.return_value = [m_dist]
        
        from sysagent.collectors.software import get_package_managers_summary
        summary = get_package_managers_summary()
        self.assertTrue(summary["pip"]["installed"])
        self.assertEqual(summary["pip"]["count"], 1)

    @patch("psutil.disk_partitions")
    @patch("psutil.disk_usage")
    def test_disk_partition_permission_denied(self, mock_usage, mock_parts):
        mock_parts.return_value = [MagicMock(device="/dev/sda1", mountpoint="/", fstype="ext4")]
        # Simulate access permission error when polling disk size details
        mock_usage.side_effect = PermissionError("Permission Denied")
        
        res = get_disk_info()
        self.assertEqual(res["partitions"][0]["total_bytes"], 0)
        self.assertEqual(res["partitions"][0]["usage_pct"], 0.0)

    @patch("os.path.exists")
    @patch("builtins.open")
    def test_ssh_keys_parsing(self, mock_open, mock_exists):
        mock_exists.return_value = True
        # Setup file iterator mock returning an SSH key entry line
        mock_file = MagicMock()
        mock_file.__iter__.return_value = ["ssh-rsa AAAAB3NzaC1yc2E... test-key-alias"]
        mock_open.return_value.__enter__.return_value = mock_file
        
        from sysagent.security.audit import check_ssh_keys
        keys = check_ssh_keys()
        self.assertEqual(len(keys), 1)
        self.assertEqual(keys[0]["comment"], "test-key-alias")

    @patch("os.path.exists")
    @patch("os.access")
    @patch("os.stat")
    @patch("sysagent.security.audit.get_platform")
    def test_world_writable_files(self, mock_plat, mock_stat, mock_access, mock_exists):
        mock_plat.return_value = "linux"
        mock_exists.return_value = True
        mock_access.return_value = True
        # Set file stats mode with world-writable bits
        mock_stat.return_value = MagicMock(st_mode=0o100777)
        
        from sysagent.security.audit import check_world_writable_files
        res = check_world_writable_files()
        self.assertTrue(len(res) > 0)
        self.assertIn("/etc/passwd", res[0])

    @patch("sys.platform", "darwin")
    def test_platform_detect_macos(self):
        from sysagent.utils.platform_detect import get_platform
        self.assertEqual(get_platform(), "macos")

    @patch("sys.platform", "linux2")
    def test_platform_detect_linux(self):
        from sysagent.utils.platform_detect import get_platform
        self.assertEqual(get_platform(), "linux")

    @patch("sys.platform", "win32")
    @patch("ctypes.windll.shell32.IsUserAnAdmin", side_effect=Exception("ctypes error"), create=True)
    def test_is_admin_windows_exception(self, mock_ctypes):
        from sysagent.utils.platform_detect import is_admin
        self.assertFalse(is_admin())

    @patch("sys.platform", "linux2")
    @patch("os.geteuid", create=True)
    def test_is_admin_linux_root(self, mock_geteuid):
        mock_geteuid.return_value = 0
        from sysagent.utils.platform_detect import is_admin
        self.assertTrue(is_admin())
        
        mock_geteuid.side_effect = Exception("geteuid error")
        self.assertFalse(is_admin())

    @patch("sys.platform", "linux2")
    def test_is_root_alias(self):
        from sysagent.utils.platform_detect import is_root
        with patch("sysagent.utils.platform_detect.is_admin") as mock_is_admin:
            is_root()
            mock_is_admin.assert_called_once()

    @patch("subprocess.run")
    def test_platform_detect_run_command_timeout(self, mock_run):
        import subprocess
        # Create TimeoutExpired exception
        exc = subprocess.TimeoutExpired(cmd=["ls"], timeout=5)
        exc.stdout = b"some partial stdout"
        exc.stderr = b"some partial stderr"
        mock_run.side_effect = exc
        
        from sysagent.utils.platform_detect import run_command
        stdout, stderr, code = run_command(["ls"], timeout=5)
        self.assertEqual(stdout, "some partial stdout")
        self.assertEqual(stderr, "some partial stderr")
        self.assertEqual(code, -1)

    @patch("subprocess.run")
    def test_platform_detect_run_command_exception(self, mock_run):
        mock_run.side_effect = Exception("subprocess error")
        from sysagent.utils.platform_detect import run_command
        stdout, stderr, code = run_command(["ls"])
        self.assertEqual(stdout, "")
        self.assertEqual(stderr, "subprocess error")
        self.assertEqual(code, -1)

    @patch("builtins.open")
    @patch("os.path.exists")
    def test_encryption_key_exceptions(self, mock_exists, mock_open):
        mock_exists.return_value = True
        # Raising exception on read
        mock_open.side_effect = Exception("Read error")
        
        from sysagent.security import encryption
        # If read fails, it generates a key and tries to write it. Let's let it generate key and test.
        with patch("sysagent.security.encryption.Fernet.generate_key") as mock_gen:
            mock_gen.return_value = b"some-generated-key"
            # mock open to raise exception on second call (write)
            mock_open.side_effect = [Exception("Read error"), Exception("Write error")]
            key = encryption.get_or_create_key()
            self.assertEqual(key, b"some-generated-key")

    @patch("builtins.open")
    def test_encryption_file_write_read_exceptions(self, mock_open):
        mock_open.side_effect = Exception("File IO error")
        from sysagent.security import encryption
        
        with self.assertRaises(Exception):
            encryption.encrypt_file("dummy.enc", "content")
            
        with self.assertRaises(Exception):
            encryption.decrypt_report("dummy.enc")

    def test_sandbox_rate_limiting_and_modify(self):
        from sysagent.security.sandbox import SandboxedCollector
        from sysagent.config import Config
        
        cfg = MagicMock(spec=Config)
        cfg.read_only_mode = True
        
        sandbox = SandboxedCollector(config=cfg)
        sandbox.register_collector("dummy", lambda: {"status": "ok"})
        
        import sysagent.security.sandbox as sandbox_module
        sandbox_module._last_scan_time = 0.0
        
        # first call
        res1 = sandbox.call_tool("get_full_report")
        
        # second call immediately
        res2 = sandbox.call_tool("get_full_report")
        self.assertTrue(res2.get("rate_limited"))
        
        # test modifying tool with read_only_mode = True
        res3 = sandbox.call_tool("set_system_time")
        self.assertIn("blocked", res3.get("error", ""))
        
        # test modifying tool with read_only_mode = False
        cfg.read_only_mode = False
        res4 = sandbox.call_tool("set_system_time")
        self.assertIn("Unknown tool", res4.get("error", ""))

    @patch("builtins.open")
    def test_sandbox_audit_write_exception(self, mock_open):
        mock_open.side_effect = Exception("Write permission denied")
        from sysagent.security.sandbox import write_audit_record
        write_audit_record("test_tool", 100)

    def test_sandbox_collector_exceptions(self):
        from sysagent.security.sandbox import SandboxedCollector
        sandbox = SandboxedCollector()
        def faulty_collector():
            raise ValueError("Data retrieval failed")
        sandbox.register_collector("faulty", faulty_collector)
        
        res = sandbox.call_tool("faulty")
        self.assertIn("Collector execution failed", res.get("error", ""))

    @patch("cpuinfo.get_cpu_info")
    @patch("psutil.cpu_freq")
    @patch("psutil.cpu_percent")
    @patch("psutil.sensors_temperatures", create=True)
    def test_cpu_collector_exceptions(self, mock_temps, mock_percent, mock_freq, mock_cpuinfo):
        mock_cpuinfo.side_effect = Exception("cpuinfo error")
        mock_freq.side_effect = Exception("cpu_freq error")
        mock_percent.side_effect = Exception("cpu_percent error")
        mock_temps.side_effect = Exception("sensors_temperatures error")
        
        from sysagent.collectors.cpu import get_cpu_info
        info = get_cpu_info()
        self.assertEqual(info["model"], "Unknown CPU")
        self.assertEqual(info["frequency_current_mhz"], 0.0)
        self.assertEqual(info["usage_overall_pct"], 0.0)
        self.assertIsNone(info["temperature_c"])

    @patch("psutil.sensors_temperatures", create=True)
    def test_cpu_temperature_fallbacks(self, mock_temps):
        mock_temps.return_value = {}
        from sysagent.collectors.cpu import get_cpu_temperature
        self.assertIsNone(get_cpu_temperature())
        
        entry = MagicMock()
        entry.current = 42.5
        mock_temps.return_value = {"random_sensor": [entry]}
        self.assertEqual(get_cpu_temperature(), 42.5)

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    def test_memory_collector_exceptions(self, mock_swap, mock_virtual):
        mock_virtual.side_effect = Exception("virtual memory error")
        mock_swap.side_effect = Exception("swap memory error")
        
        from sysagent.collectors.memory import get_memory_info
        info = get_memory_info()
        self.assertEqual(info["ram_total_bytes"], 0)
        self.assertEqual(info["swap_total_bytes"], 0)

    @patch("sysagent.collectors.memory.get_platform")
    @patch("sysagent.collectors.memory.run_command")
    def test_memory_hardware_specs_windows(self, mock_run, mock_plat):
        mock_plat.return_value = "windows"
        
        mock_run.return_value = ("Speed=2400\nMemoryType=24", "", 0)
        from sysagent.collectors.memory import get_memory_hardware_specs
        specs = get_memory_hardware_specs()
        self.assertEqual(specs["speed_mhz"], "2400 MHz")
        self.assertEqual(specs["type"], "DDR3")
        
        mock_run.side_effect = Exception("WMI error")
        specs_err = get_memory_hardware_specs()
        self.assertEqual(specs_err["speed_mhz"], "Unknown")

    @patch("sysagent.collectors.memory.get_platform")
    @patch("sysagent.collectors.memory.is_admin")
    @patch("sysagent.collectors.memory.run_command")
    def test_memory_hardware_specs_linux(self, mock_run, mock_admin, mock_plat):
        mock_plat.return_value = "linux"
        
        mock_admin.return_value = False
        from sysagent.collectors.memory import get_memory_hardware_specs
        specs_non_admin = get_memory_hardware_specs()
        self.assertEqual(specs_non_admin["speed_mhz"], "Unknown")
        
        mock_admin.return_value = True
        mock_run.return_value = ("Speed: 3200 MT/s\nType: DDR4", "", 0)
        specs_admin = get_memory_hardware_specs()
        self.assertEqual(specs_admin["speed_mhz"], "3200 MT/s")
        self.assertEqual(specs_admin["type"], "DDR4")
        
        mock_run.side_effect = Exception("dmidecode run error")
        specs_err = get_memory_hardware_specs()
        self.assertEqual(specs_err["speed_mhz"], "Unknown")

    @patch("psutil.disk_partitions")
    @patch("psutil.disk_io_counters")
    def test_disk_collector_exceptions(self, mock_io, mock_parts):
        mock_parts.side_effect = Exception("partitions error")
        mock_io.side_effect = Exception("io error")
        from sysagent.collectors.disk import get_disk_info
        info = get_disk_info()
        self.assertEqual(len(info["partitions"]), 0)
        self.assertEqual(info["io_read_bytes"], 0)

    @patch("shutil.which")
    @patch("sysagent.collectors.disk.run_command")
    def test_disk_smartctl_checks(self, mock_run, mock_which):
        mock_which.return_value = "/usr/sbin/smartctl"
        
        mock_run.return_value = ("", "", 1)
        from sysagent.collectors.disk import get_disk_info
        info = get_disk_info()
        self.assertEqual(info["smart_status"], "Not available (no drives scanned by smartctl)")
        
        mock_run.side_effect = [
            ("/dev/sda -d ata\n/dev/sdb -d ata", "", 0),
            ("SMART Health Status: OK", "", 0),
            ("SMART Health Status: FAILED", "", 0)
        ]
        info2 = get_disk_info()
        self.assertIn("/dev/sda: HEALTHY", info2["smart_status"])
        self.assertIn("/dev/sdb: CRITICAL - FAILING", info2["smart_status"])

    @patch("psutil.pids")
    @patch("psutil.process_iter")
    def test_processes_collector_exceptions(self, mock_iter, mock_pids):
        mock_pids.side_effect = Exception("pids error")
        mock_iter.side_effect = Exception("iter error")
        from sysagent.collectors.processes import get_processes
        info = get_processes()
        self.assertEqual(info["total_processes"], 0)
        self.assertEqual(len(info["top_cpu"]), 0)

    @patch("sysagent.collectors.processes.get_platform")
    @patch("sysagent.collectors.processes.run_command")
    def test_processes_services_crossplatform(self, mock_run, mock_plat):
        mock_plat.return_value = "macos"
        mock_run.return_value = ("PID\tStatus\tLabel\n123\t0\tcom.apple.finder\n-\t0\tcom.apple.unused", "", 0)
        from sysagent.collectors.processes import get_running_services
        svcs_mac = get_running_services()
        self.assertEqual(len(svcs_mac), 1)
        self.assertEqual(svcs_mac[0]["name"], "com.apple.finder")
        
        mock_plat.return_value = "linux"
        mock_run.return_value = ("dbus.service\tloaded\tactive\trunning\tSystem Message Bus", "", 0)
        svcs_linux = get_running_services()
        self.assertEqual(len(svcs_linux), 1)
        self.assertEqual(svcs_linux[0]["name"], "dbus")
        
        mock_plat.return_value = "windows"
        mock_run.return_value = ("DisplayName=Windows Audio\nName=Audiosrv\n\nDisplayName=DHCP Client\nName=Dhcp\n", "", 0)
        svcs_win = get_running_services()
        self.assertEqual(len(svcs_win), 2)
        self.assertEqual(svcs_win[0]["name"], "Audiosrv")
        self.assertEqual(svcs_win[1]["name"], "Dhcp")
        
        mock_run.side_effect = Exception("Command failed")
        svcs_err = get_running_services()
        self.assertEqual(len(svcs_err), 0)

    @patch("psutil.sensors_battery")
    @patch("sysagent.collectors.battery.get_platform")
    @patch("sysagent.collectors.battery.run_command")
    def test_battery_collector_more(self, mock_run, mock_plat, mock_battery):
        bat = MagicMock()
        bat.percent = 80.5
        bat.power_plugged = False
        bat.secsleft = 7200
        mock_battery.return_value = bat
        mock_plat.return_value = "macos"
        mock_run.return_value = ("Cycle Count: 120", "", 0)
        
        from sysagent.collectors.battery import get_battery_info
        info = get_battery_info()
        self.assertEqual(info["status"], "Discharging")
        self.assertEqual(info["time_remaining_str"], "2h 0m")
        self.assertEqual(info["cycle_count"], "120")
        
        bat.power_plugged = True
        bat.secsleft = psutil.POWER_TIME_UNLIMITED
        info_chg = get_battery_info()
        self.assertEqual(info_chg["status"], "Charging")
        self.assertEqual(info_chg["time_remaining_str"], "Unlimited / Plugged In")
        
        mock_run.side_effect = Exception("profiler error")
        info_mac_err = get_battery_info()
        self.assertEqual(info_mac_err["cycle_count"], "N/A")

