import os
import sys
import subprocess
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger("sysagent.utils.platform_detect")

def get_platform() -> str:
    """Returns 'windows', 'macos', or 'linux'."""
    plat = sys.platform.lower()
    if plat.startswith("win"):
        return "windows"
    elif plat.startswith("darwin"):
        return "macos"
    else:
        return "linux"

def is_admin() -> bool:
    """Checks if current user has administrator/root permissions."""
    if get_platform() == "windows":
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        try:
            return os.geteuid() == 0
        except Exception:
            return False

def is_root() -> bool:
    """Alias for is_admin for compatibility."""
    return is_admin()

def run_command(cmd_list: List[str], timeout: int = 10) -> Tuple[str, str, int]:
    """
    Executes a system command safely without shell=True.
    Returns (stdout, stderr, exit_code).
    """
    logger.debug(f"Running command: {cmd_list}")
    try:
        res = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False
        )
        return res.stdout.strip(), res.stderr.strip(), res.returncode
    except subprocess.TimeoutExpired as e:
        logger.warning(f"Command timed out after {timeout}s: {cmd_list}")
        stdout = e.stdout.decode('utf-8', errors='ignore') if e.stdout else ""
        stderr = e.stderr.decode('utf-8', errors='ignore') if e.stderr else "TimeoutExpired"
        return stdout.strip(), stderr.strip(), -1
    except Exception as e:
        logger.error(f"Failed to execute command {cmd_list}: {str(e)}")
        return "", str(e), -1
