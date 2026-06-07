import logging
import psutil
import cpuinfo
from typing import Dict, Any, Optional

logger = logging.getLogger("sysagent.collectors.cpu")

def get_cpu_info() -> Dict[str, Any]:
    """Collects complete CPU specs and current metrics."""
    logger.debug("Collecting CPU details...")
    info: Dict[str, Any] = {}
    
    # Static details using cpuinfo
    try:
        brand_info = cpuinfo.get_cpu_info()
        info["model"] = brand_info.get("brand_raw", "Unknown CPU")
        info["architecture"] = brand_info.get("arch", "Unknown Arch")
        info["socket"] = brand_info.get("socket", "Unknown Socket")
        info["cache_l1_data"] = brand_info.get("l1_data_cache_size", "Unknown")
        info["cache_l1_instruction"] = brand_info.get("l1_instruction_cache_size", "Unknown")
        info["cache_l2"] = brand_info.get("l2_cache_size", "Unknown")
        info["cache_l3"] = brand_info.get("l3_cache_size", "Unknown")
    except Exception as e:
        logger.warning(f"Failed to gather static CPU info from cpuinfo: {e}")
        info["model"] = "Unknown CPU"
        info["architecture"] = "Unknown Arch"
        info["socket"] = "Unknown Socket"
        info["cache_l1_data"] = "Unknown"
        info["cache_l1_instruction"] = "Unknown"
        info["cache_l2"] = "Unknown"
        info["cache_l3"] = "Unknown"

    # Cores
    info["physical_cores"] = psutil.cpu_count(logical=False) or 0
    info["logical_cores"] = psutil.cpu_count(logical=True) or 0

    # Frequencies
    try:
        freq = psutil.cpu_freq()
        if freq:
            info["frequency_current_mhz"] = round(freq.current, 2)
            info["frequency_min_mhz"] = round(freq.min, 2)
            info["frequency_max_mhz"] = round(freq.max, 2)
        else:
            info["frequency_current_mhz"] = 0.0
            info["frequency_min_mhz"] = 0.0
            info["frequency_max_mhz"] = 0.0
    except Exception as e:
        logger.warning(f"Failed to read CPU frequency: {e}")
        info["frequency_current_mhz"] = 0.0
        info["frequency_min_mhz"] = 0.0
        info["frequency_max_mhz"] = 0.0

    # Usage
    try:
        # Non-blocking per-core percentage
        info["usage_per_core_pct"] = psutil.cpu_percent(interval=0.1, percpu=True)
        info["usage_overall_pct"] = psutil.cpu_percent(interval=None)
    except Exception as e:
        logger.warning(f"Failed to read CPU usage percentages: {e}")
        info["usage_per_core_pct"] = []
        info["usage_overall_pct"] = 0.0

    # Temperature
    info["temperature_c"] = get_cpu_temperature()

    return info

def get_cpu_temperature() -> Optional[float]:
    """Helper to read CPU temperature via psutil, falls back gracefully."""
    try:
        temps = psutil.sensors_temperatures()
        if not temps:
            return None
        
        # Check standard CPU temperature label targets
        for label in ["coretemp", "cpu-thermal", "cpu_thermal", "acpitz", "k10temp"]:
            if label in temps:
                entries = temps[label]
                if entries:
                    # Return first valid current temp
                    return round(entries[0].current, 2)
        
        # General fallback: return first entry of any sensor
        for label, entries in temps.items():
            if entries:
                return round(entries[0].current, 2)
    except Exception as e:
        logger.debug(f"Sensors temperature read failed or unsupported: {e}")
    
    return None
