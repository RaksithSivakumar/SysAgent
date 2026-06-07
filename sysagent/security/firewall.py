import os
import socket
import logging
import psutil
from typing import Dict, Any, List
from sysagent.utils.platform_detect import get_platform, run_command

logger = logging.getLogger("sysagent.security.firewall")

def get_firewall_info() -> Dict[str, Any]:
    """Retrieves firewall configuration details and analyzes open listening ports."""
    logger.debug("Auditing firewall and open ports...")
    return {
        "status": get_firewall_status(),
        "listening_ports": get_listening_ports()
    }

def get_firewall_status() -> str:
    """Detects native firewall status on the host OS."""
    plat = get_platform()

    if plat == "windows":
        try:
            # Query Windows Defender Firewall state
            stdout, stderr, code = run_command(["netsh", "advfirewall", "show", "allprofiles", "state"])
            if code == 0 and stdout:
                states = []
                for line in stdout.splitlines():
                    if "State" in line:
                        states.append(line.strip())
                if states:
                    return "; ".join(states)
                return "Defender Firewall: Installed (Check output manually)"
        except Exception as e:
            logger.debug(f"Failed to query netsh advfirewall: {e}")

    elif plat == "macos":
        try:
            # Check Application Layer Firewall (ALF) state
            stdout, stderr, code = run_command([
                "defaults", "read", "/Library/Preferences/com.apple.alf", "globalstate"
            ])
            if code == 0 and stdout:
                val = stdout.strip()
                if val == "0":
                    return "macOS PF/ALF: Disabled"
                elif val in ("1", "2"):
                    return "macOS PF/ALF: Enabled"
                return f"macOS PF/ALF: Status {val}"
        except Exception as e:
            logger.debug(f"Failed to read macOS ALF settings: {e}")

    elif plat == "linux":
        # Check ufw
        try:
            stdout, stderr, code = run_command(["ufw", "status"])
            if code == 0 and stdout:
                return f"UFW: {stdout.splitlines()[0].strip()}"
        except Exception:
            pass
            
        # Check iptables (requires root)
        try:
            stdout, stderr, code = run_command(["iptables", "-L", "-n"])
            if code == 0:
                return "iptables: Active (rules present)"
        except Exception:
            pass

    return "Unknown / Not Detected"

def get_listening_ports() -> List[Dict[str, Any]]:
    """
    Checks all active listening sockets on the host.
    Flags any port open to 0.0.0.0 or :: that is not 80/443.
    """
    ports = []
    seen = set()
    
    try:
        conns = psutil.net_connections(kind="inet")
        for conn in conns:
            if conn.status == "LISTEN":
                ip = conn.laddr.ip
                port = conn.laddr.port
                
                # Create unique key
                key = (ip, port, conn.type)
                if key in seen:
                    continue
                seen.add(key)
                
                # Flag if listening on all interfaces (0.0.0.0 or [::]) and not 80/443
                is_all_interfaces = ip in ("0.0.0.0", "::", "*")
                is_secure_web = port in (80, 443)
                
                warning = False
                warning_reason = ""
                if is_all_interfaces and not is_secure_web:
                    warning = True
                    warning_reason = f"Port {port} is exposed to all interfaces (0.0.0.0/::) and is not standard HTTP/S (80/443)."

                ports.append({
                    "port": port,
                    "address": ip,
                    "proto": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                    "pid": conn.pid or "N/A",
                    "exposed_warning": warning,
                    "warning_reason": warning_reason
                })
    except Exception as e:
        logger.warning(f"Could not read listening ports from net_connections: {e}")
        # Try a quick fallback using process connections
        try:
            p_conns = psutil.Process().connections()
            for conn in p_conns:
                if conn.status == "LISTEN":
                    ip = conn.laddr.ip
                    port = conn.laddr.port
                    ports.append({
                        "port": port,
                        "address": ip,
                        "proto": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                        "pid": os.getpid(),
                        "exposed_warning": ip in ("0.0.0.0", "::") and port not in (80, 443),
                        "warning_reason": "Process-bound port open to external interface" if ip in ("0.0.0.0", "::") else ""
                    })
        except Exception:
            pass
            
    # Sort ports by port number
    return sorted(ports, key=lambda x: x["port"])
