import os
import sys
import shutil
import logging
import json
from typing import Dict, Any, List, Optional
from sysagent.utils.platform_detect import run_command

logger = logging.getLogger("sysagent.collectors.software")

def get_software_info() -> Dict[str, Any]:
    """Collects system development tools, Docker, Git, virtualenv, and package counts."""
    logger.debug("Collecting Software details...")
    info: Dict[str, Any] = {}

    # Python and active virtualenv
    info["python_version"] = sys.version.split()[0]
    info["virtualenv"] = os.environ.get("VIRTUAL_ENV", "None (Global System)")

    # Git
    git_ver = get_tool_version(["git", "--version"])
    info["git_installed"] = git_ver is not None
    info["git_version"] = git_ver or "Not installed"

    # Docker status
    info["docker"] = get_docker_status()

    # Common Developer Tools
    info["dev_tools"] = {
        "node": get_tool_version(["node", "--version"]) or "Not installed",
        "npm": get_tool_version(["npm", "--version"]) or "Not installed",
        "rust": get_tool_version(["rustc", "--version"]) or "Not installed",
        "go": get_tool_version(["go", "version"]) or "Not installed"
    }

    # Installed Package Managers and Package Lists (Summarized to save space)
    info["package_managers"] = get_package_managers_summary()

    return info

def get_tool_version(cmd: List[str]) -> Optional[str]:
    """Checks if a tool is present and returns its version string."""
    binary = cmd[0]
    if not shutil.which(binary):
        return None
    try:
        stdout, stderr, code = run_command(cmd, timeout=3)
        if code == 0:
            return stdout.strip()
    except Exception:
        pass
    return None

def get_docker_status() -> Dict[str, Any]:
    """Checks if Docker is installed and running, along with active containers."""
    status = {"installed": False, "running": False, "version": "Not installed", "containers": []}
    
    docker_bin = shutil.which("docker")
    if not docker_bin:
        return status

    status["installed"] = True
    
    # Get version
    ver = get_tool_version([docker_bin, "--version"])
    if ver:
        status["version"] = ver

    # Check if daemon is running
    stdout, stderr, code = run_command([docker_bin, "info"], timeout=5)
    if code == 0:
        status["running"] = True
        
        # Get active containers list
        c_stdout, c_stderr, c_code = run_command([
            docker_bin, "ps", "--format", "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}"
        ], timeout=5)
        
        if c_code == 0 and c_stdout:
            for line in c_stdout.splitlines():
                line = line.strip()
                if line and "|" in line:
                    parts = line.split("|")
                    if len(parts) >= 4:
                        status["containers"].append({
                            "id": parts[0],
                            "name": parts[1],
                            "status": parts[2],
                            "image": parts[3]
                        })
    return status

def get_package_managers_summary() -> Dict[str, Any]:
    """Detects packages from available package managers (pip, winget, apt, brew)."""
    summary = {}

    # 1. Pip (Python Packages via importlib.metadata)
    try:
        import importlib.metadata
        dists = list(importlib.metadata.distributions())
        # Return first 30 package names + total count
        pkg_names = sorted([d.metadata["Name"] for d in dists if d.metadata.get("Name")])
        summary["pip"] = {
            "installed": True,
            "count": len(pkg_names),
            "sample": pkg_names[:30]
        }
    except Exception as e:
        logger.debug(f"Failed to query pip distributions: {e}")
        summary["pip"] = {"installed": False, "count": 0, "sample": []}

    # 2. Brew (macOS Package Manager)
    brew_bin = shutil.which("brew")
    if brew_bin:
        try:
            stdout, stderr, code = run_command([brew_bin, "list", "--formula"], timeout=5)
            if code == 0:
                pkgs = sorted(stdout.split())
                summary["brew"] = {
                    "installed": True,
                    "count": len(pkgs),
                    "sample": pkgs[:30]
                }
        except Exception:
            pass
    if "brew" not in summary:
        summary["brew"] = {"installed": False, "count": 0, "sample": []}

    # 3. Apt (Debian/Ubuntu Package Manager)
    apt_bin = shutil.which("apt-mark")
    if apt_bin:
        try:
            # Check manually installed packages
            stdout, stderr, code = run_command([apt_bin, "showmanual"], timeout=5)
            if code == 0:
                pkgs = sorted(stdout.split())
                summary["apt"] = {
                    "installed": True,
                    "count": len(pkgs),
                    "sample": pkgs[:30]
                }
        except Exception:
            pass
    if "apt" not in summary:
        summary["apt"] = {"installed": False, "count": 0, "sample": []}

    # 4. Winget (Windows Package Manager)
    winget_bin = shutil.which("winget")
    if winget_bin:
        # Winget is slow and interactive. We just verify availability or count
        summary["winget"] = {
            "installed": True,
            "count": "Available (Skipping list output to prevent timeout)",
            "sample": []
        }
    else:
        summary["winget"] = {"installed": False, "count": 0, "sample": []}

    return summary
