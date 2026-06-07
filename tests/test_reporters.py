import json
import unittest
from sysagent.config import Config
from sysagent.reporters.json_report import generate_json
from sysagent.reporters.markdown_report import generate_markdown
from sysagent.reporters.html_report import generate_html
from sysagent.reporters.alert import AlertEngine

class TestReporters(unittest.TestCase):

    def setUp(self):
        # Sample system telemetry dataset
        self.data = {
            "get_os_info": {
                "os_name": "Windows",
                "os_version": "11",
                "uptime_str": "5 hours",
                "hostname": "TestPC",
                "logged_in_users": ["alice"]
            },
            "get_cpu_info": {
                "model": "Test CPU",
                "architecture": "x64",
                "physical_cores": 4,
                "logical_cores": 8,
                "usage_overall_pct": 95.0, # High CPU usage (threshold 90)
                "temperature_c": 65.0
            },
            "get_memory_info": {
                "ram_total_bytes": 16000000000,
                "ram_used_bytes": 14000000000,
                "ram_usage_pct": 87.5, # High Memory usage (threshold 85)
                "swap_total_bytes": 2000000000,
                "swap_used_bytes": 0,
                "swap_usage_pct": 0.0
            },
            "get_disk_info": {
                "partitions": [
                    {
                        "device": "C:",
                        "mountpoint": "/",
                        "fstype": "NTFS",
                        "usage_pct": 92.0, # High Disk usage (threshold 90)
                        "total_bytes": 100000000000,
                        "free_bytes": 8000000000
                    }
                ],
                "smart_status": "Healthy"
            },
            "get_gpu_info": {
                "gpu_detected": False,
                "gpus": []
            },
            "get_network_info": {
                "interfaces": [
                    {
                        "name": "Ethernet",
                        "status": "UP",
                        "ipv4": "192.168.1.10",
                        "mac": "00:11:22:33:44:55",
                        "bytes_sent": 500000,
                        "bytes_recv": 1500000
                    }
                ],
                "dns_servers": ["8.8.8.8"]
            },
            "get_firewall_info": {
                "listening_ports": [
                    {
                        "port": 8080,
                        "address": "0.0.0.0",
                        "proto": "TCP",
                        "exposed_warning": True,
                        "warning_reason": "Exposed custom port"
                    }
                ]
            },
            "get_security_audit": {
                "admin_users": ["Administrator"],
                "world_writable_files": ["/etc/passwd"]
            },
            "get_software_info": {
                "python_version": "3.11.2",
                "virtualenv": "None"
            }
        }
        self.config = Config(
            cpu_usage_pct=90.0,
            memory_usage_pct=85.0,
            disk_usage_pct=90.0,
            battery_pct=10.0
        )

    def test_json_reporter(self):
        json_str = generate_json(self.data, "gemini-2.0-flash")
        parsed = json.loads(json_str)
        self.assertIn("metadata", parsed)
        self.assertIn("system_data", parsed)
        self.assertEqual(parsed["metadata"]["model_used"], "gemini-2.0-flash")
        self.assertEqual(parsed["system_data"]["get_os_info"]["hostname"], "TestPC")

    def test_markdown_reporter(self):
        md_str = generate_markdown(self.data)
        self.assertIn("# SysAgent System Report", md_str)
        self.assertIn("Test CPU", md_str)
        self.assertIn("TestPC", md_str)

    def test_html_reporter(self):
        html_str = generate_html(self.data)
        self.assertIn("<!DOCTYPE html>", html_str)
        self.assertIn("<title>SysAgent Dashboard", html_str)
        self.assertIn("TestPC", html_str)

    def test_alert_engine_triggers(self):
        engine = AlertEngine(self.config, self.data)
        alerts = engine.check_all()
        
        # We expect CPU warning, RAM warning, Disk C: critical, firewall port warning, world writable file warning
        alert_messages = [a.message for a in alerts]
        alert_levels = [a.level for a in alerts]
        
        self.assertTrue(any("CPU usage is high" in msg for msg in alert_messages))
        self.assertTrue(any("Memory RAM usage is high" in msg for msg in alert_messages))
        self.assertTrue(any("Disk partition" in msg for msg in alert_messages))
        self.assertTrue(any("Exposed custom port" in msg for msg in alert_messages))
        
        self.assertIn("WARNING", alert_levels)
        self.assertIn("CRITICAL", alert_levels)
