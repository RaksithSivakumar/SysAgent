import logging
from google.generativeai.types import FunctionDeclaration, Tool

logger = logging.getLogger("sysagent.agent.tools")

def build_tools() -> Tool:
    """Builds and returns a single Tool wrapping all system intelligence FunctionDeclarations."""
    
    get_cpu_info = FunctionDeclaration(
        name="get_cpu_info",
        description="Returns CPU specs, cores, clock speeds, current utilization, caches and temperature.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_memory_info = FunctionDeclaration(
        name="get_memory_info",
        description="Returns system memory details including total/used/free RAM, Swap usage, speed and type.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_disk_info = FunctionDeclaration(
        name="get_disk_info",
        description="Returns partition storage capacities, IO read/write stats, and SMART status summaries.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_gpu_info = FunctionDeclaration(
        name="get_gpu_info",
        description="Returns information on detected graphics cards: model, VRAM usage, temperature, load and driver.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_network_info = FunctionDeclaration(
        name="get_network_info",
        description="Returns adapter interfaces, active IPv4/IPv6, MAC, bytes Tx/Rx, sockets, and DNS servers.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_battery_info = FunctionDeclaration(
        name="get_battery_info",
        description="Returns battery presence, charge level percent, charging status, time left, and cycle count.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_os_info = FunctionDeclaration(
        name="get_os_info",
        description="Returns host kernel version, build number, hostnames, logged-in sessions, timezone and safe env vars.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_processes = FunctionDeclaration(
        name="get_processes",
        description="Returns total count, top 10 CPU/Memory hogs, and currently running system services.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_software_info = FunctionDeclaration(
        name="get_software_info",
        description="Returns Python layout, virtualenvs, Git versions, running Docker containers, and package managers.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_security_audit = FunctionDeclaration(
        name="get_security_audit",
        description="Returns local security checks including admin accounts, writable files, active SSH keys, and recent audit log events.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    get_full_report = FunctionDeclaration(
        name="get_full_report",
        description="Compiles and returns a complete system profile including all hardware, software, network, and security data.",
        parameters={
            "type": "OBJECT",
            "properties": {}
        }
    )

    return Tool(function_declarations=[
        get_cpu_info,
        get_memory_info,
        get_disk_info,
        get_gpu_info,
        get_network_info,
        get_battery_info,
        get_os_info,
        get_processes,
        get_software_info,
        get_security_audit,
        get_full_report
    ])
