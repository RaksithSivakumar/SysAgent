import os
import tempfile
import json
import unittest
from unittest.mock import patch, MagicMock

from sysagent.config import Config
from sysagent.security.sandbox import SandboxedCollector, write_audit_record
from sysagent.security.encryption import encrypt_data, decrypt_data, encrypt_file, decrypt_report

class TestSecurity(unittest.TestCase):

    def setUp(self):
        # Setup test configuration
        self.config = Config(
            model="gemini-2.0-flash",
            read_only_mode=True,
            cache_ttl_seconds=30
        )

    @patch("sysagent.security.sandbox.write_audit_record")
    def test_sandbox_read_only_blocks_modifications(self, mock_audit):
        sandbox = SandboxedCollector(self.config)
        # Register a dummy write tool
        sandbox.register_collector("execute_write_something", lambda: {"status": "success"})
        
        # Calling write tool should block it and return warning
        res = sandbox.call_tool("execute_write_something")
        self.assertIn("error", res)
        self.assertIn("blocked", res["error"])
        mock_audit.assert_called_with("execute_write_something", 0)

    @patch("sysagent.security.sandbox.write_audit_record")
    def test_sandbox_executes_registered_read_only(self, mock_audit):
        sandbox = SandboxedCollector(self.config)
        sandbox.register_collector("get_cpu_info", lambda: {"cores": 4})
        
        res = sandbox.call_tool("get_cpu_info")
        self.assertEqual(res["cores"], 4)
        mock_audit.assert_called_once()

    def test_encryption_decryption_round_trip(self):
        secret_data = "System telemetry reports: No issues found."
        
        # Encrypt
        encrypted = encrypt_data(secret_data)
        self.assertIsInstance(encrypted, bytes)
        self.assertNotEqual(encrypted.decode("utf-8", errors="ignore"), secret_data)
        
        # Decrypt
        decrypted = decrypt_data(encrypted)
        self.assertEqual(decrypted, secret_data)

    def test_encrypted_file_read_write(self):
        secret_content = '{"status": "OK", "temp": 34.5}'
        with tempfile.TemporaryDirectory() as tempdir:
            filepath = os.path.join(tempdir, "report.enc")
            
            # Write encrypted file
            encrypt_file(filepath, secret_content)
            self.assertTrue(os.path.exists(filepath))
            
            # Verify file content is encrypted (not plain JSON)
            with open(filepath, "rb") as f:
                raw_bytes = f.read()
            self.assertNotIn(b"status", raw_bytes)
            
            # Decrypt back
            decrypted = decrypt_report(filepath)
            self.assertEqual(decrypted, secret_content)

    @patch("psutil.net_connections")
    @patch("sysagent.security.firewall.get_firewall_status")
    def test_firewall_exposed_ports(self, mock_status, mock_conns):
        mock_status.return_value = "Windows Defender: Enabled"
        
        # Mock listening socket on 0.0.0.0:8080 (should flag warning) and 127.0.0.1:443
        c1 = MagicMock(status="LISTEN", type=1) # TCP
        c1.laddr.ip = "0.0.0.0"
        c1.laddr.port = 8080
        c1.pid = 1000
        
        c2 = MagicMock(status="LISTEN", type=1)
        c2.laddr.ip = "127.0.0.1"
        c2.laddr.port = 443
        c2.pid = 1001

        mock_conns.return_value = [c1, c2]

        from sysagent.security.firewall import get_firewall_info
        info = get_firewall_info()
        
        self.assertEqual(info["status"], "Windows Defender: Enabled")
        self.assertEqual(len(info["listening_ports"]), 2)
        
        # Verify exposure warnings
        warnings = [p for p in info["listening_ports"] if p["exposed_warning"]]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0]["port"], 8080)

    @patch("sysagent.security.audit.run_command")
    @patch("sysagent.security.audit.is_admin")
    def test_security_audit_accounts_and_files(self, mock_is_admin, mock_cmd):
        mock_is_admin.return_value = True
        # Mock net localgroup administrators output
        mock_cmd.return_value = ("Alias name     administrators\n-----------------\nAdministrator\nAlice\nThe command completed successfully.", "", 0)
        
        from sysagent.security.audit import get_security_audit
        audit = get_security_audit()
        
        self.assertIn("Administrator", audit["admin_users"])
        self.assertIn("Alice", audit["admin_users"])
        self.assertIsInstance(audit["world_writable_files"], list)
        self.assertIsInstance(audit["ssh_keys"], list)

