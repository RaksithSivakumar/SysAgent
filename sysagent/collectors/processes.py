import logging
import psutil
from typing import Dict, Any, List
from sysagent.utils.platform_detect import get_platform, run_command

logger = logging.getLogger("sysagent.collectors.processes")

def get_processes() -> Dict[str, Any]:
    """Collects system process statistics, resource hogs, and active service lists."""
    logger.debug("Collecting Processes details...")
    info: Dict[str, Any] = {}

    # Total process count
    try:
        pids = psutil.pids()
        info["total_processes"] = len(pids)
    except Exception as e:
        logger.error(f"Failed to read process IDs list: {e}")
        info["total_processes"] = 0

    # Build process list
    proc_list: List[Dict[str, Any]] = []
    try:
        # Scan all processes
        for proc in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent"]):
            try:
                pinfo = proc.info
                # Handle possible None values
                cpu_val = pinfo.get("cpu_percent") or 0.0
                mem_val = pinfo.get("memory_percent") or 0.0
                proc_list.append({
                    "pid": pinfo.get("pid"),
                    "name": pinfo.get("name") or "Unknown",
                    "cpu_pct": round(cpu_val, 2),
                    "memory_pct": round(mem_val, 2)
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception as e:
        logger.error(f"Error iterating processes: {e}")

    # Top 10 by CPU
    info["top_cpu"] = sorted(proc_list, key=lambda x: x["cpu_pct"], reverse=True)[:10]

    # Top 10 by Memory
    info["top_memory"] = sorted(proc_list, key=lambda x: x["memory_pct"], reverse=True)[:10]

    # Running Services
    info["services"] = get_running_services()

    return info

def get_running_services() -> List[Dict[str, str]]:
    """Retrieves list of active system services (systemd, Windows SCM, macOS launchd)."""
    plat = get_platform()
    services: List[Dict[str, str]] = []

    if plat == "windows":
        try:
            # Query SCM via wmic
            stdout, stderr, code = run_command(["wmic", "service", "where", "State='Running'", "get", "Name,DisplayName", "/format:list"])
            if code == 0 and stdout:
                current_service: Dict[str, str] = {}
                for line in stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        current_service[k.strip()] = v.strip()
                        if len(current_service) == 2:
                            services.append({
                                "name": current_service.get("Name", ""),
                                "status": "Running",
                                "description": current_service.get("DisplayName", "")
                            })
                            current_service = {}
        except Exception as e:
            logger.debug(f"Failed to read Windows SCM services: {e}")

    elif plat == "linux":
        try:
            # Query systemd
            stdout, stderr, code = run_command(["systemctl", "list-units", "--type=service", "--state=running", "--no-legend", "--plain"])
            if code == 0 and stdout:
                for line in stdout.splitlines():
                    parts = line.strip().split(None, 4)
                    if len(parts) >= 4:
                        name = parts[0].replace(".service", "")
                        desc = parts[4] if len(parts) > 4 else ""
                        services.append({
                            "name": name,
                            "status": "Running",
                            "description": desc
                        })
        except Exception as e:
            logger.debug(f"Failed to read Linux systemd services: {e}")

    elif plat == "macos":
        try:
            # Query launchd
            stdout, stderr, code = run_command(["launchctl", "list"])
            if code == 0 and stdout:
                # launchctl list prints: PID Status Label
                for line in stdout.splitlines():
                    parts = line.strip().split()
                    if len(parts) >= 3 and parts[0].isdigit(): # PID is present, so it is running
                        services.append({
                            "name": parts[2],
                            "status": "Running",
                            "description": f"PID: {parts[0]}"
                        })
        except Exception as e:
            logger.debug(f"Failed to read macOS launchd jobs: {e}")

    return services
