import logging
import psutil
from typing import Dict, Any, Optional
from sysagent.utils.platform_detect import get_platform, run_command, is_admin

logger = logging.getLogger("sysagent.collectors.memory")

def get_memory_info() -> Dict[str, Any]:
    """Collects system RAM, Swap and memory chip details."""
    logger.debug("Collecting Memory details...")
    info: Dict[str, Any] = {}

    # RAM details
    try:
        virtual_mem = psutil.virtual_memory()
        info["ram_total_bytes"] = virtual_mem.total
        info["ram_available_bytes"] = virtual_mem.available
        info["ram_used_bytes"] = virtual_mem.used
        info["ram_usage_pct"] = virtual_mem.percent
    except Exception as e:
        logger.error(f"Failed to gather virtual memory info: {e}")
        info["ram_total_bytes"] = 0
        info["ram_available_bytes"] = 0
        info["ram_used_bytes"] = 0
        info["ram_usage_pct"] = 0.0

    # Swap details
    try:
        swap_mem = psutil.swap_memory()
        info["swap_total_bytes"] = swap_mem.total
        info["swap_used_bytes"] = swap_mem.used
        info["swap_free_bytes"] = swap_mem.free
        info["swap_usage_pct"] = swap_mem.percent
    except Exception as e:
        logger.error(f"Failed to gather swap memory info: {e}")
        info["swap_total_bytes"] = 0
        info["swap_used_bytes"] = 0
        info["swap_free_bytes"] = 0
        info["swap_usage_pct"] = 0.0

    # Hardware Specs (Speed, Type)
    hw = get_memory_hardware_specs()
    info["speed_mhz"] = hw.get("speed_mhz")
    info["type"] = hw.get("type")

    return info

def get_memory_hardware_specs() -> Dict[str, Any]:
    """
    Retrieves RAM speed and type.
    Uses 'wmic' on Windows and 'dmidecode' on Linux (if root).
    """
    plat = get_platform()
    specs = {"speed_mhz": "Unknown", "type": "Unknown"}

    if plat == "windows":
        try:
            # Run wmic memorychip get Speed, MemoryType, TypeDetail
            stdout, stderr, code = run_command(["wmic", "memorychip", "get", "Speed,MemoryType", "/format:list"])
            if code == 0 and stdout:
                speeds = []
                types = []
                for line in stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("Speed="):
                        val = line.split("=", 1)[1].strip()
                        if val and val != "0":
                            speeds.append(val)
                    elif line.startswith("MemoryType="):
                        val = line.split("=", 1)[1].strip()
                        if val and val != "0":
                            types.append(val)
                if speeds:
                    specs["speed_mhz"] = f"{speeds[0]} MHz"
                if types:
                    # Map WMI MemoryType enum to human readable
                    wmi_type_map = {
                        "20": "DDR", "21": "DDR2", "22": "DDR2 FB-DIMM",
                        "24": "DDR3", "26": "DDR4", "34": "DDR5"
                    }
                    t_val = types[0]
                    specs["type"] = wmi_type_map.get(t_val, f"Type enum {t_val}")
        except Exception as e:
            logger.debug(f"Failed to get WMI memory hardware specs: {e}")

    elif plat == "linux":
        if is_admin():
            try:
                # dmidecode --type 17 requires root
                stdout, stderr, code = run_command(["dmidecode", "--type", "17"])
                if code == 0 and stdout:
                    speed = "Unknown"
                    mtype = "Unknown"
                    for line in stdout.splitlines():
                        line = line.strip()
                        if line.startswith("Speed:") and "Unknown" not in line:
                            speed = line.split(":", 1)[1].strip()
                        elif line.startswith("Type:") and "Unknown" not in line:
                            mtype = line.split(":", 1)[1].strip()
                    specs["speed_mhz"] = speed
                    specs["type"] = mtype
            except Exception as e:
                logger.debug(f"Failed to read dmidecode memory info: {e}")
        else:
            logger.debug("dmidecode memory check skipped - requires root permissions.")

    return specs
