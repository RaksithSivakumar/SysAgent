import os
import logging
import psutil
from typing import Dict, Any
from sysagent.utils.platform_detect import get_platform, run_command

logger = logging.getLogger("sysagent.collectors.battery")

def get_battery_info() -> Dict[str, Any]:
    """Collects system battery information."""
    logger.debug("Collecting Battery details...")
    info: Dict[str, Any] = {
        "present": False,
        "charge_pct": 0,
        "status": "No battery detected",
        "time_remaining_str": "N/A",
        "cycle_count": "N/A"
    }

    try:
        battery = psutil.sensors_battery()
        if battery is None:
            return info

        info["present"] = True
        info["charge_pct"] = round(battery.percent, 2)
        
        # Charging/Discharging status
        if battery.power_plugged:
            info["status"] = "Charging" if battery.percent < 100 else "Full"
        else:
            info["status"] = "Discharging"

        # Time remaining
        secs = battery.secsleft
        if secs == psutil.POWER_TIME_UNLIMITED:
            info["time_remaining_str"] = "Unlimited / Plugged In"
        elif secs == psutil.POWER_TIME_UNKNOWN:
            info["time_remaining_str"] = "Calculating..."
        else:
            hours = secs // 3600
            minutes = (secs % 3600) // 60
            info["time_remaining_str"] = f"{hours}h {minutes}m"

        # Cycle count (platform specific fallback)
        info["cycle_count"] = get_battery_cycle_count()
    except Exception as e:
        logger.warning(f"Failed to read battery statistics: {e}")

    return info

def get_battery_cycle_count() -> Any:
    """Retrieves battery cycle count on macOS/Linux if available."""
    plat = get_platform()

    if plat == "macos":
        try:
            # Query system_profiler SPPowerDataType
            stdout, stderr, code = run_command(["system_profiler", "SPPowerDataType"])
            if code == 0 and stdout:
                for line in stdout.splitlines():
                    if "Cycle Count:" in line:
                        return line.split(":", 1)[1].strip()
        except Exception as e:
            logger.debug(f"macOS battery cycle count query failed: {e}")

    elif plat == "linux":
        try:
            # Check standard sysfs path
            for bat in ["BAT0", "BAT1", "BATC"]:
                path = f"/sys/class/power_supply/{bat}/cycle_count"
                if os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as f:
                        val = f.read().strip()
                        if val:
                            return int(val)
        except Exception as e:
            logger.debug(f"Linux battery cycle count query failed: {e}")

    return "N/A"
