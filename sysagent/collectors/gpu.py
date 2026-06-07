import logging
from typing import Dict, Any, List
from sysagent.utils.platform_detect import get_platform, run_command

logger = logging.getLogger("sysagent.collectors.gpu")

def get_gpu_info() -> Dict[str, Any]:
    """Collects GPU details. Uses GPUtil first, then falls back to platform commands."""
    logger.debug("Collecting GPU details...")
    info: Dict[str, Any] = {"gpu_detected": False, "gpus": []}

    # 1. Try GPUtil (NVIDIA specific)
    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if gpus:
            info["gpu_detected"] = True
            for g in gpus:
                info["gpus"].append({
                    "name": g.name,
                    "vendor": "NVIDIA",
                    "vram_total_mb": round(g.memoryTotal, 2),
                    "vram_used_mb": round(g.memoryUsed, 2),
                    "vram_free_mb": round(g.memoryFree, 2),
                    "temperature_c": g.temperature,
                    "load_pct": round(g.load * 100, 2),
                    "driver_version": getattr(g, "driver", "Unknown NVIDIA Driver")
                })
            return info
    except Exception as e:
        logger.debug(f"GPUtil check failed or not installed: {e}")

    # 2. Fallback to Platform Specific Queries (Intel/AMD/Others)
    plat = get_platform()
    if plat == "windows":
        try:
            # Query WMI for general video controller
            stdout, stderr, code = run_command([
                "wmic", "path", "win32_VideoController", "get",
                "Name,AdapterRAM,DriverVersion,VideoProcessor", "/format:list"
            ])
            if code == 0 and stdout:
                gpu_data: Dict[str, str] = {}
                for line in stdout.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        gpu_data[k.strip()] = v.strip()
                
                # Check if we parsed a name
                if gpu_data.get("Name"):
                    info["gpu_detected"] = True
                    ram_bytes = int(gpu_data.get("AdapterRAM") or 0)
                    ram_mb = round(ram_bytes / (1024 * 1024), 2) if ram_bytes > 0 else "Unknown"
                    vendor = "Unknown"
                    name_lower = gpu_data["Name"].lower()
                    if "nvidia" in name_lower:
                        vendor = "NVIDIA"
                    elif "intel" in name_lower:
                        vendor = "Intel"
                    elif "amd" in name_lower or "radeon" in name_lower:
                        vendor = "AMD"

                    info["gpus"].append({
                        "name": gpu_data["Name"],
                        "vendor": vendor,
                        "vram_total_mb": ram_mb,
                        "vram_used_mb": "Unknown",
                        "vram_free_mb": "Unknown",
                        "temperature_c": "Unknown",
                        "load_pct": "Unknown",
                        "driver_version": gpu_data.get("DriverVersion", "Unknown")
                    })
        except Exception as e:
            logger.debug(f"WMI GPU query failed: {e}")

    elif plat == "linux":
        try:
            # Query lspci for VGA compatible controllers
            stdout, stderr, code = run_command(["lspci", "-v"])
            if code == 0 and stdout:
                for line in stdout.splitlines():
                    if "VGA compatible controller" in line or "3D controller" in line:
                        info["gpu_detected"] = True
                        name = line.split(":", 2)[-1].strip()
                        vendor = "Unknown"
                        name_lower = name.lower()
                        if "nvidia" in name_lower:
                            vendor = "NVIDIA"
                        elif "intel" in name_lower:
                            vendor = "Intel"
                        elif "amd" in name_lower or "ati" in name_lower:
                            vendor = "AMD"

                        info["gpus"].append({
                            "name": name,
                            "vendor": vendor,
                            "vram_total_mb": "Unknown",
                            "vram_used_mb": "Unknown",
                            "vram_free_mb": "Unknown",
                            "temperature_c": "Unknown",
                            "load_pct": "Unknown",
                            "driver_version": "Unknown"
                        })
        except Exception as e:
            logger.debug(f"lspci GPU query failed: {e}")

    elif plat == "macos":
        try:
            # Mac system_profiler SPDisplaysDataType
            stdout, stderr, code = run_command(["system_profiler", "SPDisplaysDataType"])
            if code == 0 and stdout:
                lines = stdout.splitlines()
                gpu_name = None
                vram = None
                for line in lines:
                    line = line.strip()
                    if line.startswith("Chipset Model:"):
                        gpu_name = line.split(":", 1)[1].strip()
                    elif line.startswith("VRAM (Total):"):
                        vram = line.split(":", 1)[1].strip()
                if gpu_name:
                    info["gpu_detected"] = True
                    info["gpus"].append({
                        "name": gpu_name,
                        "vendor": "Apple" if "apple" in gpu_name.lower() else "Unknown",
                        "vram_total_mb": vram or "Unknown",
                        "vram_used_mb": "Unknown",
                        "vram_free_mb": "Unknown",
                        "temperature_c": "Unknown",
                        "load_pct": "Unknown",
                        "driver_version": "N/A"
                    })
        except Exception as e:
            logger.debug(f"macOS system_profiler GPU check failed: {e}")

    # No GPU detected
    if not info["gpus"]:
        info["gpus"].append({
            "name": "Not available",
            "vendor": "Not available",
            "vram_total_mb": 0,
            "vram_used_mb": 0,
            "vram_free_mb": 0,
            "temperature_c": 0,
            "load_pct": 0,
            "driver_version": "Not available"
        })

    return info
