import os
import sys
import time
import socket
import locale
import logging
import platform
import datetime
import psutil
from typing import Dict, Any, List
from sysagent.utils.platform_detect import get_platform, run_command

logger = logging.getLogger("sysagent.collectors.os_info")

def get_os_info() -> Dict[str, Any]:
    """Collects operating system parameters, hostname, uptime, locale, and active users."""
    logger.debug("Collecting OS details...")
    info: Dict[str, Any] = {}

    # Host and Kernel details
    info["os_name"] = platform.system()
    info["os_version"] = platform.release()
    info["os_build"] = platform.version()
    info["kernel_version"] = platform.uname().release
    info["hostname"] = socket.gethostname()
    
    # Machine ID
    info["machine_id"] = get_machine_id()

    # System Uptime
    info["uptime_seconds"] = get_uptime_seconds()
    info["uptime_str"] = get_uptime_human(info["uptime_seconds"])

    # Logged-in users
    users: List[str] = []
    try:
        current_users = psutil.users()
        for u in current_users:
            users.append(u.name)
        info["logged_in_users"] = list(set(users))
    except Exception as e:
        logger.warning(f"Failed to fetch logged in users: {e}")
        info["logged_in_users"] = []

    # Filtered Environment variables
    info["environment_variables"] = get_safe_environment()

    # Locale and Timezone
    try:
        info["locale"] = ".".join(filter(None, locale.getdefaultlocale()))
    except Exception:
        info["locale"] = "Unknown"
        
    try:
        info["timezone"] = datetime.datetime.now(datetime.timezone.utc).astimezone().tzname() or "UTC"
    except Exception:
        info["timezone"] = "Unknown"

    return info

def get_machine_id() -> str:
    """Gets the system's unique hardware identifier across platforms."""
    plat = get_platform()
    if plat == "windows":
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            )
            val, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            return str(val).strip()
        except Exception as e:
            logger.debug(f"Failed to read Windows MachineGuid registry: {e}")

    elif plat == "linux":
        for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        return f.read().strip()
                except Exception as e:
                    logger.debug(f"Failed to read machine-id at {path}: {e}")

    elif plat == "macos":
        try:
            stdout, stderr, code = run_command(["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"])
            if code == 0 and stdout:
                for line in stdout.splitlines():
                    if "IOPlatformUUID" in line:
                        return line.split("=", 1)[1].replace('"', "").strip()
        except Exception as e:
            logger.debug(f"Failed to fetch macOS platform UUID: {e}")

    return "Unknown Machine ID"

def get_uptime_seconds() -> float:
    """Calculates seconds elapsed since system boot."""
    try:
        boot_time = psutil.boot_time()
        return time.time() - boot_time
    except Exception as e:
        logger.warning(f"Uptime calculation failed: {e}")
        return 0.0

def get_uptime_human(seconds: float) -> str:
    """Converts seconds into a readable day, hour, minute representation."""
    if seconds <= 0:
        return "Unknown"
    delta = datetime.timedelta(seconds=int(seconds))
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0:
        parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0 or not parts:
        parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        
    return ", ".join(parts)

def get_safe_environment() -> Dict[str, str]:
    """Exposes a whitelisted subset of environment variables, avoiding sensitive keys."""
    whitelist = {
        "PATH", "LANG", "SHELL", "USER", "USERNAME", "OS", "COMPUTERNAME",
        "HOME", "USERPROFILE", "VIRTUAL_ENV", "TERM", "PWD", "LOGNAME", "PYTHONPATH"
    }
    safe_env = {}
    for key, val in os.environ.items():
        if key.upper() in whitelist:
            safe_env[key] = val
        else:
            # Explicitly drop items containing key indicator terms to prevent accidental leaks
            sensitive_terms = ["KEY", "PASSWORD", "SECRET", "TOKEN", "AUTH", "CREDENTIAL", "API", "PASS"]
            if any(term in key.upper() for term in sensitive_terms):
                continue
            # Include basic harmless-looking vars
            if len(key) < 25 and len(val) < 150:
                safe_env[key] = val
    return safe_env
