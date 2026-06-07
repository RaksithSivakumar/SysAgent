import logging
import psutil
import shutil
from typing import Dict, Any, List
from sysagent.utils.platform_detect import get_platform, run_command

logger = logging.getLogger("sysagent.collectors.disk")

def get_disk_info() -> Dict[str, Any]:
    """Collects disk partitions, usage, disk IO, and SMART diagnostics."""
    logger.debug("Collecting Disk details...")
    info: Dict[str, Any] = {}

    # Partitions and usages
    partitions_list: List[Dict[str, Any]] = []
    try:
        parts = psutil.disk_partitions(all=False)
        for part in parts:
            # Skip empty or helper mountpoints
            if not part.mountpoint:
                continue
            
            p_info = {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "opts": part.opts
            }
            
            try:
                usage = psutil.disk_usage(part.mountpoint)
                p_info["total_bytes"] = usage.total
                p_info["used_bytes"] = usage.used
                p_info["free_bytes"] = usage.free
                p_info["usage_pct"] = usage.percent
            except Exception as e:
                # Permission errors or drives not ready (CD-ROMs, empty card readers)
                logger.debug(f"Could not read disk usage for mount {part.mountpoint}: {e}")
                p_info["total_bytes"] = 0
                p_info["used_bytes"] = 0
                p_info["free_bytes"] = 0
                p_info["usage_pct"] = 0.0

            partitions_list.append(p_info)
    except Exception as e:
        logger.error(f"Failed to read disk partitions: {e}")

    info["partitions"] = partitions_list

    # Disk IO
    try:
        io = psutil.disk_io_counters()
        if io:
            info["io_read_bytes"] = io.read_bytes
            info["io_write_bytes"] = io.write_bytes
            info["io_read_count"] = io.read_count
            info["io_write_count"] = io.write_count
        else:
            info["io_read_bytes"] = 0
            info["io_write_bytes"] = 0
            info["io_read_count"] = 0
            info["io_write_count"] = 0
    except Exception as e:
        logger.warning(f"Failed to read disk IO counters: {e}")
        info["io_read_bytes"] = 0
        info["io_write_bytes"] = 0
        info["io_read_count"] = 0
        info["io_write_count"] = 0

    # SMART summary
    info["smart_status"] = get_smart_summary()

    return info

def get_smart_summary() -> str:
    """Checks SMART status of drives using smartctl if installed."""
    smartctl_path = shutil.which("smartctl")
    if not smartctl_path:
        return "Not available (smartmontools not installed)"

    # Probe for drives using smartctl --scan
    stdout, stderr, code = run_command([smartctl_path, "--scan"])
    if code != 0 or not stdout:
        return "Not available (no drives scanned by smartctl)"

    drives = []
    for line in stdout.splitlines():
        parts = line.strip().split()
        if parts:
            drives.append(parts[0]) # e.g. /dev/sda or /dev/nvme0

    if not drives:
        return "Not available (no drives found)"

    results = []
    # Test first 2 drives to avoid long wait
    for drive in drives[:2]:
        out, err, exit_code = run_command([smartctl_path, "-H", drive])
        if "PASSED" in out or "OK" in out:
            results.append(f"{drive}: HEALTHY")
        elif "FAILED" in out:
            results.append(f"{drive}: CRITICAL - FAILING")
        else:
            results.append(f"{drive}: UNKNOWN")
            
    return ", ".join(results)
