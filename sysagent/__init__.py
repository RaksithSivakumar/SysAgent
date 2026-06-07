# SysAgent - AI-Powered System Intelligence Agent
__version__ = "0.1.0"

import sys
for _stream in (sys.stdout, sys.stderr):
    if _stream and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from sysagent.utils.logger import setup_logger
from sysagent.config import Config
try:
    _c = Config.load()
    setup_logger(_c.log_level)
except Exception:
    setup_logger("INFO")


