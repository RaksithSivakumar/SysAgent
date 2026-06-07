import os
import time
import logging
import unittest
from unittest.mock import patch

from sysagent.utils.cache import SimpleCache
from sysagent.utils.logger import setup_logger
from sysagent.utils.platform_detect import get_platform, is_admin, run_command

class TestUtils(unittest.TestCase):

    def test_simple_cache_ttl(self):
        cache = SimpleCache(default_ttl=1)
        cache.set("key1", "value1")
        self.assertEqual(cache.get("key1"), "value1")
        
        # Test expiration
        time.sleep(1.1)
        self.assertIsNone(cache.get("key1"))

        # Test clear
        cache.set("key2", "value2")
        cache.clear()
        self.assertIsNone(cache.get("key2"))

    def test_platform_checkers(self):
        plat = get_platform()
        self.assertIn(plat, ("windows", "macos", "linux"))

        admin_status = is_admin()
        self.assertIsInstance(admin_status, bool)

    def test_run_command_safe(self):
        # Test basic echo command
        stdout, stderr, code = run_command(["python", "--version"])
        # Should execute successfully or report exit code / error gracefully
        self.assertIsInstance(code, int)

    def test_setup_logger(self):
        logger = setup_logger("DEBUG")
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertTrue(len(logger.handlers) > 0)
