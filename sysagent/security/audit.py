import os
import sys
import time
import json
import logging
from typing import Dict, Any, List
from sysagent.utils.platform_detect import get_platform, run_command, is_admin

logger = logging.getLogger("sysagent.security.audit")

def get_security_audit() -> Dict[str, Any]:
    """Compiles a complete local security audit report."""
    logger.debug("Running security audit...")
    return {
        "admin_users": get_admin_users(),
        "world_writable_files": check_world_writable_files(),
        "ssh_keys": check_ssh_keys(),
        "recent_modified_system_files": check_recent_modified_system_files(),
        "audit_logs": get_recent_audit_logs()
    }

def get_recent_audit_logs(limit: int = 50) -> List[Dict[str, Any]]:
    """Parses and returns the last N entries of ~/.sysagent/audit.log."""
    home = os.path.expanduser("~")
    audit_path = os.path.join(home, ".sysagent", "audit.log")
    logs = []
    if not os.path.exists(audit_path):
        return logs
    try:
        with open(audit_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Return last N lines
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    logs.append(json.loads(line))
    except Exception as e:
        logger.error(f"Failed to read audit log file: {e}")
    return logs

def get_admin_users() -> List[str]:
    """Retrieves list of privileged administrator/sudo users on the host."""
    plat = get_platform()
    admins = []

    if plat == "windows":
        try:
            stdout, stderr, code = run_command(["net", "localgroup", "administrators"])
            if code == 0 and stdout:
                lines = stdout.splitlines()
                # Administrators are listed after the separator lines ----
                start_parsing = False
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if "-----------------" in line:
                        start_parsing = True
                        continue
                    if start_parsing:
                        if "The command completed successfully" in line:
                            break
                        admins.append(line)
        except Exception as e:
            logger.debug(f"Failed to check net localgroup administrators: {e}")

    elif plat == "macos":
        try:
            stdout, stderr, code = run_command(["dscl", ".", "-read", "/Groups/admin", "GroupMembership"])
            if code == 0 and stdout and ":" in stdout:
                parts = stdout.split(":", 1)
                admins = parts[1].strip().split()
        except Exception as e:
            logger.debug(f"Failed to check macOS admin group: {e}")

    elif plat == "linux":
        try:
            # Check /etc/group for sudo and admin
            if os.path.exists("/etc/group"):
                with open("/etc/group", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("sudo:") or line.startswith("admin:"):
                            parts = line.split(":")
                            if len(parts) >= 4 and parts[3]:
                                admins.extend(parts[3].split(","))
            # Also check if root is present
            admins.append("root")
        except Exception as e:
            logger.debug(f"Failed to check Linux admin groups: {e}")

    return list(set(admins))

def check_world_writable_files() -> List[str]:
    """
    Checks specific critical path files/directories for unsafe write access.
    Avoids checking entire disks to prevent performance bottlenecks.
    """
    plat = get_platform()
    unsafe = []

    # 1. Critical config files
    targets = []
    if plat == "windows":
        # Check system hosts file
        windir = os.environ.get("WINDIR", "C:\\Windows")
        targets.append(os.path.join(windir, "System32\\drivers\\etc\\hosts"))
    else:
        # Check Linux/macOS passwd, hosts, resolv.conf
        targets.extend(["/etc/passwd", "/etc/hosts", "/etc/resolv.conf"])

    for path in targets:
        if os.path.exists(path):
            try:
                # Check write permissions
                if os.access(path, os.W_OK):
                    # On Windows, os.access(path, os.W_OK) is true if write is allowed.
                    # On Unix, check if world writable by group/other
                    if plat != "windows":
                        stat = os.stat(path)
                        # Check last two octets (world / group write: 0o002 or 0o020)
                        if stat.st_mode & 0o002:
                            unsafe.append(f"{path} (World-Writable)")
                    else:
                        # On Windows, we'd check if standard users have write access,
                        # for this simple agent, just flag if not running as admin but writeable.
                        if not is_admin() and os.access(path, os.W_OK):
                            unsafe.append(f"{path} (Writeable by User)")
            except Exception:
                pass

    return unsafe

def check_ssh_keys() -> List[Dict[str, Any]]:
    """Checks SSH authorized_keys file of the current user for key count and comments."""
    plat = get_platform()
    keys = []
    home = os.path.expanduser("~")
    ssh_path = os.path.join(home, ".ssh", "authorized_keys")

    if os.path.exists(ssh_path):
        try:
            with open(ssh_path, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split()
                    key_type = parts[0] if len(parts) > 0 else "Unknown"
                    comment = parts[2] if len(parts) > 2 else "No comment"
                    keys.append({
                        "index": idx + 1,
                        "type": key_type,
                        "comment": comment
                    })
        except Exception as e:
            logger.warning(f"Failed to parse SSH authorized_keys: {e}")
            
    return keys

def check_recent_modified_system_files() -> List[Dict[str, Any]]:
    """Checks configuration directories for files modified in the past 24 hours."""
    plat = get_platform()
    recent_files = []
    now = time.time()
    day_seconds = 24 * 60 * 60

    search_dirs = []
    if plat == "windows":
        windir = os.environ.get("WINDIR", "C:\\Windows")
        search_dirs.append(os.path.join(windir, "System32\\drivers\\etc"))
    else:
        search_dirs.append("/etc")

    for sdir in search_dirs:
        if os.path.exists(sdir):
            try:
                # Walk only top level to prevent infinite scans
                for entry in os.scandir(sdir):
                    if entry.is_file():
                        try:
                            mtime = entry.stat().st_mtime
                            if now - mtime < day_seconds:
                                age_hours = round((now - mtime) / 3600, 2)
                                recent_files.append({
                                    "path": entry.path,
                                    "modified_hours_ago": age_hours
                                })
                                if len(recent_files) >= 15: # cap at 15 files
                                    break
                        except Exception:
                            pass
            except Exception:
                pass

    return recent_files
