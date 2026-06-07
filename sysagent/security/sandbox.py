import os
import time
import json
import getpass
import logging
from datetime import datetime
from typing import Dict, Any, Callable, Optional
from sysagent.config import Config

logger = logging.getLogger("sysagent.security.sandbox")

# In-memory track for rate limiting
_last_scan_time: float = 0.0

def _get_audit_log_path() -> str:
    home = os.path.expanduser("~")
    sysagent_dir = os.path.join(home, ".sysagent")
    os.makedirs(sysagent_dir, exist_ok=True)
    return os.path.join(sysagent_dir, "audit.log")

def write_audit_record(tool_name: str, result_size_bytes: int):
    """Writes a structured record to ~/.sysagent/audit.log."""
    try:
        audit_path = _get_audit_log_path()
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "tool": tool_name,
            "user": getpass.getuser(),
            "result_size_bytes": result_size_bytes
        }
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")

class SandboxedCollector:
    """
    Wrapper for system information collectors.
    Ensures safe operations, audits calls, and enforces read-only mode and rate limits.
    """
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config.load()
        self._registry: Dict[str, Callable[[], Dict[str, Any]]] = {}

    def register_collector(self, name: str, func: Callable[[], Dict[str, Any]]):
        """Registers a collector function under a standard tool name."""
        self._registry[name] = func

    def call_tool(self, name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a registered tool securely, applying audits, rate limits and read-only checks.
        """
        global _last_scan_time

        logger.info(f"Sandbox executing tool: {name}")

        # Enforce rate limit on full scans (get_full_report or scan command equivalent)
        if name in ("get_full_report", "scan"):
            current_time = time.time()
            elapsed = current_time - _last_scan_time
            if elapsed < 60.0:
                warning_msg = f"Rate limit active: full scan allowed once per 60s. Wait {int(60.0 - elapsed)}s."
                logger.warning(warning_msg)
                return {
                    "status": "error",
                    "error": warning_msg,
                    "rate_limited": True
                }
            _last_scan_time = current_time

        # If the requested tool is a write/modify action and we are read_only_mode, we must block it.
        # Although all default tools are read-only, we implement this check for completeness.
        is_modifying = name.startswith("set_") or name.startswith("modify_") or name.startswith("execute_write_")
        if is_modifying:
            log_msg = f"Unauthorized modifying operation '{name}' requested in read-only sandbox mode."
            logger.error(log_msg)
            
            # Log to audit.log
            write_audit_record(name, 0)
            
            if self.config.read_only_mode:
                return {
                    "status": "error",
                    "error": f"Security Alert: Operation '{name}' blocked. Running in read-only sandbox mode."
                }
            else:
                # Interactive prompt if needed (handled in CLI/REPL usually, or fallback to auto-allow if not interactive)
                logger.warning(f"Modifying operation '{name}' approved under write-enabled configuration.")

        if name not in self._registry:
            err_msg = f"Unknown tool or collector: {name}"
            logger.error(err_msg)
            return {"status": "error", "error": err_msg}

        try:
            # Execute the actual collector function
            collector_func = self._registry[name]
            result = collector_func()
            
            # Audit the result size
            result_str = json.dumps(result)
            write_audit_record(name, len(result_str.encode("utf-8")))
            
            return result
        except Exception as e:
            err_msg = f"Collector execution failed for '{name}': {str(e)}"
            logger.exception(err_msg)
            write_audit_record(name, 0)
            return {"status": "error", "error": err_msg}

    def get_full_report(self) -> Dict[str, Any]:
        """Runs all registered collectors to compile a full system profile."""
        report = {}
        for name in list(self._registry.keys()):
            if name != "get_full_report":
                report[name] = self.call_tool(name)
        return report
