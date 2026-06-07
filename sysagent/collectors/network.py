import os
import socket
import logging
import psutil
from typing import Dict, Any, List
from sysagent.utils.platform_detect import get_platform, run_command

logger = logging.getLogger("sysagent.collectors.network")

def get_network_info() -> Dict[str, Any]:
    """Collects complete network information including interfaces, traffic, connections, and DNS."""
    logger.debug("Collecting Network details...")
    info: Dict[str, Any] = {}

    # Interfaces details
    interfaces: List[Dict[str, Any]] = []
    try:
        addrs = psutil.net_if_addrs()
        stats = psutil.net_if_stats()
        io_counters = psutil.net_io_counters(pernic=True)

        for name, addr_list in addrs.items():
            iface_stats = stats.get(name)
            iface_io = io_counters.get(name)

            ipv4 = None
            ipv6 = None
            mac = None

            for addr in addr_list:
                if addr.family == socket.AF_INET:
                    ipv4 = addr.address
                elif addr.family == getattr(socket, "AF_INET6", -1):
                    ipv6 = addr.address
                elif addr.family == getattr(psutil, "AF_LINK", -1) or addr.family == socket.AF_UNSPEC:
                    mac = addr.address

            iface_info = {
                "name": name,
                "ipv4": ipv4 or "N/A",
                "ipv6": ipv6 or "N/A",
                "mac": mac or "N/A",
                "speed_mbps": iface_stats.speed if iface_stats else 0,
                "mtu": iface_stats.mtu if iface_stats else 0,
                "status": "UP" if (iface_stats and iface_stats.isup) else "DOWN",
                "bytes_sent": iface_io.bytes_sent if iface_io else 0,
                "bytes_recv": iface_io.bytes_recv if iface_io else 0
            }
            interfaces.append(iface_info)
    except Exception as e:
        logger.error(f"Failed to gather interfaces information: {e}")

    info["interfaces"] = interfaces

    # Open Connections
    connections: List[Dict[str, Any]] = []
    try:
        # psutil.net_connections can throw PermissionError
        conns = psutil.net_connections(kind="inet")
        for conn in conns:
            laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
            raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
            connections.append({
                "fd": conn.fd,
                "family": str(conn.family),
                "type": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                "local_address": laddr,
                "remote_address": raddr,
                "status": conn.status,
                "pid": conn.pid or "N/A"
            })
    except psutil.AccessDenied:
        logger.warning("Access denied when reading net_connections (needs higher privileges).")
        # Fallback: try reading connections for this process only, to return at least something
        try:
            p_conns = psutil.Process().connections()
            for conn in p_conns:
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else ""
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else ""
                connections.append({
                    "fd": conn.fd,
                    "family": str(conn.family),
                    "type": "TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                    "local_address": laddr,
                    "remote_address": raddr,
                    "status": conn.status,
                    "pid": os.getpid()
                })
        except Exception as e:
            logger.debug(f"Process connection read fallback failed: {e}")
    except Exception as e:
        logger.error(f"Failed to read system net_connections: {e}")

    info["connections"] = connections
    info["dns_servers"] = get_dns_servers()

    return info

def get_dns_servers() -> List[str]:
    """Retrieves list of configured DNS servers."""
    plat = get_platform()
    dns: List[str] = []

    if plat == "windows":
        try:
            # Query ipconfig /all
            stdout, stderr, code = run_command(["ipconfig", "/all"])
            if code == 0 and stdout:
                found_dns_section = False
                for line in stdout.splitlines():
                    line = line.strip()
                    if "DNS Servers" in line:
                        found_dns_section = True
                        dns_val = line.split(":", 1)[1].strip()
                        if dns_val:
                            dns.append(dns_val)
                    elif found_dns_section and line and ":" not in line:
                        # IP config prints subsequent DNS entries on new lines without keys
                        dns.append(line.strip())
                    elif found_dns_section and line and ":" in line:
                        # Reached next config key
                        break
        except Exception as e:
            logger.debug(f"Failed to read DNS on Windows: {e}")
            
    else:
        # Linux/macOS
        try:
            if os.path.exists("/etc/resolv.conf"):
                with open("/etc/resolv.conf", "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("nameserver"):
                            parts = line.split()
                            if len(parts) > 1:
                                dns.append(parts[1])
        except Exception as e:
            logger.debug(f"Failed to read resolv.conf: {e}")

    # Clean up empty strings or invalid IPs
    dns = [d for d in dns if d and not d.startswith("::") and d.lower() != "fec0::"]
    return list(set(dns)) if dns else ["8.8.8.8", "8.8.4.4"] # safe default fallback if empty
