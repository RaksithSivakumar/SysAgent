import time
import unittest
from unittest.mock import patch, MagicMock

# Import collectors
from sysagent.collectors.cpu import get_cpu_info
from sysagent.collectors.memory import get_memory_info
from sysagent.collectors.disk import get_disk_info
from sysagent.collectors.gpu import get_gpu_info
from sysagent.collectors.network import get_network_info
from sysagent.collectors.battery import get_battery_info
from sysagent.collectors.os_info import get_os_info
from sysagent.collectors.processes import get_processes
from sysagent.collectors.software import get_software_info

class TestCollectors(unittest.TestCase):
    
    @patch("psutil.cpu_count")
    @patch("psutil.cpu_freq")
    @patch("psutil.cpu_percent")
    @patch("psutil.sensors_temperatures", create=True)
    @patch("cpuinfo.get_cpu_info")
    def test_cpu_collector(self, mock_cpuinfo, mock_temps, mock_percent, mock_freq, mock_count):
        mock_cpuinfo.return_value = {
            "brand_raw": "Intel Core i7-10700K CPU @ 3.80GHz",
            "arch": "X86_64",
            "socket": "LGA1200",
            "l1_data_cache_size": 262144,
            "l1_instruction_cache_size": 262144,
            "l2_cache_size": 2097152,
            "l3_cache_size": 16777216
        }
        mock_count.return_value = 8
        mock_freq.return_value = MagicMock(current=3800.0, min=800.0, max=5100.0)
        mock_percent.return_value = 15.5
        
        mock_entry = MagicMock()
        mock_entry.current = 45.0
        mock_temps.return_value = {"coretemp": [mock_entry]}

        res = get_cpu_info()
        self.assertEqual(res["model"], "Intel Core i7-10700K CPU @ 3.80GHz")
        self.assertEqual(res["architecture"], "X86_64")
        self.assertEqual(res["physical_cores"], 8)
        self.assertEqual(res["logical_cores"], 8)
        self.assertEqual(res["frequency_current_mhz"], 3800.0)
        self.assertEqual(res["temperature_c"], 45.0)

    @patch("psutil.virtual_memory")
    @patch("psutil.swap_memory")
    @patch("sysagent.collectors.memory.get_memory_hardware_specs")
    def test_memory_collector(self, mock_hw, mock_swap, mock_virtual):
        mock_virtual.return_value = MagicMock(total=17179869184, available=8589934592, used=8589934592, percent=50.0)
        mock_swap.return_value = MagicMock(total=4294967296, used=1073741824, free=3221225472, percent=25.0)
        mock_hw.return_value = {"speed_mhz": "3200 MHz", "type": "DDR4"}

        res = get_memory_info()
        self.assertEqual(res["ram_total_bytes"], 17179869184)
        self.assertEqual(res["ram_usage_pct"], 50.0)
        self.assertEqual(res["swap_total_bytes"], 4294967296)
        self.assertEqual(res["swap_usage_pct"], 25.0)
        self.assertEqual(res["speed_mhz"], "3200 MHz")
        self.assertEqual(res["type"], "DDR4")

    @patch("psutil.disk_partitions")
    @patch("psutil.disk_usage")
    @patch("psutil.disk_io_counters")
    @patch("sysagent.collectors.disk.get_smart_summary")
    def test_disk_collector(self, mock_smart, mock_io, mock_usage, mock_partitions):
        mock_partitions.return_value = [
            MagicMock(device="/dev/sda1", mountpoint="/", fstype="ext4", opts="rw")
        ]
        mock_usage.return_value = MagicMock(total=250000000000, used=100000000000, free=150000000000, percent=40.0)
        mock_io.return_value = MagicMock(read_bytes=1000, write_bytes=2000, read_count=50, write_count=100)
        mock_smart.return_value = "/dev/sda1: HEALTHY"

        res = get_disk_info()
        self.assertEqual(len(res["partitions"]), 1)
        self.assertEqual(res["partitions"][0]["mountpoint"], "/")
        self.assertEqual(res["partitions"][0]["usage_pct"], 40.0)
        self.assertEqual(res["io_read_bytes"], 1000)
        self.assertEqual(res["smart_status"], "/dev/sda1: HEALTHY")

    @patch("GPUtil.getGPUs")
    def test_gpu_collector_nvidia(self, mock_get_gpus):
        mock_gpu = MagicMock()
        mock_gpu.name = "NVIDIA GeForce RTX 4070"
        mock_gpu.memoryTotal = 12288.0
        mock_gpu.memoryUsed = 2048.0
        mock_gpu.memoryFree = 10240.0
        mock_gpu.temperature = 45.0
        mock_gpu.load = 0.15
        mock_gpu.driver = "535.104"
        mock_get_gpus.return_value = [mock_gpu]

        res = get_gpu_info()
        self.assertTrue(res["gpu_detected"])
        self.assertEqual(res["gpus"][0]["name"], "NVIDIA GeForce RTX 4070")
        self.assertEqual(res["gpus"][0]["vram_total_mb"], 12288.0)
        self.assertEqual(res["gpus"][0]["load_pct"], 15.0)

    @patch("psutil.sensors_battery")
    def test_battery_collector_not_present(self, mock_battery):
        mock_battery.return_value = None
        res = get_battery_info()
        self.assertFalse(res["present"])
        self.assertEqual(res["status"], "No battery detected")

    @patch("psutil.boot_time")
    @patch("psutil.users")
    def test_os_info_collector(self, mock_users, mock_boot):
        mock_boot.return_value = time.time() - 3600 # Uptime 1 hour
        mock_user = MagicMock()
        mock_user.name = "alice"
        mock_users.return_value = [mock_user]
        
        res = get_os_info()
        self.assertIn("Alice", [u.capitalize() for u in res["logged_in_users"]])
        self.assertEqual(res["uptime_str"], "1 hour")

    @patch("psutil.net_if_addrs")
    @patch("psutil.net_if_stats")
    @patch("psutil.net_io_counters")
    @patch("psutil.net_connections")
    @patch("sysagent.collectors.network.get_dns_servers")
    def test_network_collector(self, mock_dns, mock_conns, mock_io, mock_stats, mock_addrs):
        mock_dns.return_value = ["1.1.1.1"]
        mock_conns.return_value = []
        mock_io.return_value = {"eth0": MagicMock(bytes_sent=1000, bytes_recv=2000)}
        mock_stats.return_value = {"eth0": MagicMock(speed=100, mtu=1500, isup=True)}
        
        # Mock interface address
        addr = MagicMock(family=2, address="192.168.1.5") # AF_INET
        mock_addrs.return_value = {"eth0": [addr]}

        res = get_network_info()
        self.assertEqual(len(res["interfaces"]), 1)
        self.assertEqual(res["interfaces"][0]["name"], "eth0")
        self.assertEqual(res["interfaces"][0]["ipv4"], "192.168.1.5")
        self.assertEqual(res["interfaces"][0]["status"], "UP")
        self.assertIn("1.1.1.1", res["dns_servers"])

    @patch("psutil.pids")
    @patch("psutil.process_iter")
    @patch("sysagent.collectors.processes.get_running_services")
    def test_processes_collector(self, mock_srv, mock_iter, mock_pids):
        mock_pids.return_value = [1, 2]
        p1 = MagicMock(info={"pid": 1, "name": "systemd", "cpu_percent": 1.0, "memory_percent": 2.0})
        mock_iter.return_value = [p1]
        mock_srv.return_value = [{"name": "dbus", "status": "Running", "description": "dbus"}]

        res = get_processes()
        self.assertEqual(res["total_processes"], 2)
        self.assertEqual(len(res["top_cpu"]), 1)
        self.assertEqual(res["top_cpu"][0]["name"], "systemd")
        self.assertEqual(len(res["services"]), 1)

    @patch("shutil.which")
    @patch("sysagent.collectors.software.get_tool_version")
    def test_software_collector(self, mock_ver, mock_which):
        mock_which.side_effect = lambda x: f"/usr/bin/{x}" if x in ("git", "docker") else None
        mock_ver.side_effect = lambda cmd: "2.40.0" if cmd[0] == "git" else None

        res = get_software_info()
        self.assertTrue(res["git_installed"])
        self.assertEqual(res["git_version"], "2.40.0")
        self.assertFalse(res["docker"]["running"])

    @patch("psutil.sensors_battery")
    def test_battery_collector_present(self, mock_battery):
        mock_bat = MagicMock(percent=85.0, power_plugged=True, secsleft=-1)
        mock_battery.return_value = mock_bat
        
        res = get_battery_info()
        self.assertTrue(res["present"])
        self.assertEqual(res["charge_pct"], 85.0)
        self.assertEqual(res["status"], "Charging")

