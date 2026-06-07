import socket
from datetime import datetime
from typing import Dict, Any

def generate_markdown(data: Dict[str, Any]) -> str:
    """Generates a clean markdown formatted report with tables and highlighted security findings."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    hostname = data.get("get_os_info", {}).get("hostname") or socket.gethostname()
    
    md = []
    md.append(f"# SysAgent System Report — {hostname}")
    md.append(f"**Generated:** {timestamp} | **Host:** {hostname} | **SysAgent:** v0.1.0\n")
    md.append("---")

    # 1. OS & Platform Information
    os_info = data.get("get_os_info", {})
    md.append("## 🖥️ Operating System & Machine Details")
    md.append(f"- **OS:** {os_info.get('os_name', 'N/A')} {os_info.get('os_version', 'N/A')} ({os_info.get('os_build', 'N/A')})")
    md.append(f"- **Kernel:** {os_info.get('kernel_version', 'N/A')}")
    md.append(f"- **Uptime:** {os_info.get('uptime_str', 'N/A')}")
    md.append(f"- **Locale / Timezone:** {os_info.get('locale', 'N/A')} / {os_info.get('timezone', 'N/A')}")
    md.append(f"- **Machine ID:** `{os_info.get('machine_id', 'N/A')}`")
    md.append(f"- **Logged In Users:** {', '.join(os_info.get('logged_in_users', [])) or 'None'}\n")

    # 2. CPU Details
    cpu = data.get("get_cpu_info", {})
    md.append("## ⚙️ Processor (CPU)")
    md.append(f"- **Model:** {cpu.get('model', 'N/A')} ({cpu.get('architecture', 'N/A')})")
    md.append(f"- **Cores:** {cpu.get('physical_cores', 0)} Physical | {cpu.get('logical_cores', 0)} Logical")
    md.append(f"- **Frequency:** Cur: {cpu.get('frequency_current_mhz', 0.0)} MHz | Max: {cpu.get('frequency_max_mhz', 0.0)} MHz")
    md.append(f"- **Usage:** Overall: **{cpu.get('usage_overall_pct', 0.0)}%**")
    temp = cpu.get("temperature_c")
    md.append(f"- **Temperature:** {f'{temp}°C' if temp else 'Not available'}")
    md.append(f"- **Caches:** L1d: {cpu.get('cache_l1_data', 'N/A')} | L1i: {cpu.get('cache_l1_instruction', 'N/A')} | L2: {cpu.get('cache_l2', 'N/A')} | L3: {cpu.get('cache_l3', 'N/A')}\n")

    # 3. Memory Details
    mem = data.get("get_memory_info", {})
    ram_tot = round(mem.get("ram_total_bytes", 0) / (1024**3), 2)
    ram_usd = round(mem.get("ram_used_bytes", 0) / (1024**3), 2)
    swap_tot = round(mem.get("swap_total_bytes", 0) / (1024**3), 2)
    swap_usd = round(mem.get("swap_used_bytes", 0) / (1024**3), 2)
    md.append("## 💾 Memory (RAM & Swap)")
    md.append(f"- **System RAM:** {ram_usd} GB / {ram_tot} GB (**{mem.get('ram_usage_pct', 0.0)}%** used)")
    md.append(f"- **Swap Memory:** {swap_usd} GB / {swap_tot} GB (**{mem.get('swap_usage_pct', 0.0)}%** used)")
    md.append(f"- **Hardware Type / Speed:** {mem.get('type', 'Unknown')} / {mem.get('speed_mhz', 'Unknown')}\n")

    # 4. Disk Layout
    disk = data.get("get_disk_info", {})
    md.append("## 💽 Disk Partitions & Storage")
    md.append("| Partition | Mount point | Format | Usage % | Total | Free |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for part in disk.get("partitions", []):
        tot_gb = round(part.get("total_bytes", 0) / (1024**3), 2)
        free_gb = round(part.get("free_bytes", 0) / (1024**3), 2)
        md.append(f"| `{part.get('device')}` | `{part.get('mountpoint')}` | {part.get('fstype')} | {part.get('usage_pct')}% | {tot_gb} GB | {free_gb} GB |")
    md.append(f"\n- **SMART Health Summary:** {disk.get('smart_status', 'N/A')}\n")

    # 5. GPU details
    gpu = data.get("get_gpu_info", {})
    md.append("## 🎮 Graphics Processors (GPU)")
    if gpu.get("gpu_detected"):
        for g in gpu.get("gpus", []):
            md.append(f"- **Model:** {g.get('name')} ({g.get('vendor')})")
            md.append(f"  - **VRAM:** {g.get('vram_used_mb')} MB / {g.get('vram_total_mb')} MB")
            md.append(f"  - **Load / Temp:** {g.get('load_pct')}% / {g.get('temperature_c')}°C")
            md.append(f"  - **Driver:** {g.get('driver_version')}")
    else:
        md.append("- No dedicated GPU detected / Not available.\n")

    # 6. Network Adapters
    net = data.get("get_network_info", {})
    md.append("\n## 🌐 Network Interfaces")
    md.append("| Interface | Status | IPv4 | MAC Address | Tx Bytes | Rx Bytes |")
    md.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
    for iface in net.get("interfaces", []):
        tx_mb = round(iface.get("bytes_sent", 0) / (1024**2), 2)
        rx_mb = round(iface.get("bytes_recv", 0) / (1024**2), 2)
        md.append(f"| {iface.get('name')} | **{iface.get('status')}** | {iface.get('ipv4')} | `{iface.get('mac')}` | {tx_mb} MB | {rx_mb} MB |")
    md.append(f"\n- **Configured DNS Servers:** {', '.join(net.get('dns_servers', [])) or 'None'}\n")

    # 7. Processes
    proc = data.get("get_processes", {})
    md.append("## ⚙️ Running Processes Summary")
    md.append(f"- **Total Active Processes:** {proc.get('total_processes', 0)}")
    
    md.append("\n### Top 5 CPU Consumers")
    md.append("| PID | Name | CPU % | Memory % |")
    md.append("| :--- | :--- | :--- | :--- |")
    for p in proc.get("top_cpu", [])[:5]:
        md.append(f"| {p.get('pid')} | `{p.get('name')}` | {p.get('cpu_pct')}% | {p.get('memory_pct')}% |")

    md.append("\n### Top 5 Memory Consumers")
    md.append("| PID | Name | Memory % | CPU % |")
    md.append("| :--- | :--- | :--- | :--- |")
    for p in proc.get("top_memory", [])[:5]:
        md.append(f"| {p.get('pid')} | `{p.get('name')}` | {p.get('memory_pct')}% | {p.get('cpu_pct')}% |")
    md.append("")

    # 8. Software Environment
    soft = data.get("get_software_info", {})
    md.append("## 📦 Software & Developer Tools")
    md.append(f"- **Python Version:** {soft.get('python_version', 'N/A')}")
    md.append(f"- **Active Virtualenv:** `{soft.get('virtualenv', 'None')}`")
    md.append(f"- **Git installed:** {soft.get('git_version', 'Not installed')}")
    
    docker = soft.get("docker", {})
    if docker.get("installed"):
        md.append(f"- **Docker:** Installed ({docker.get('version')}), Running: **{docker.get('running')}**")
        if docker.get("containers"):
            md.append("  - **Active Containers:**")
            for c in docker.get("containers", []):
                md.append(f"    - `{c.get('name')}` ({c.get('image')}): {c.get('status')}")
    else:
        md.append("- **Docker:** Not installed")

    dev_tools = soft.get("dev_tools", {})
    md.append("- **Common Dev Runtimes:**")
    for tool, ver in dev_tools.items():
        md.append(f"  - **{tool.capitalize()}:** {ver}")
    md.append("")

    # 9. Security Audit
    sec = data.get("get_security_audit", {})
    md.append("## 🛡️ Security Audit Findings")
    
    # Check for critical warnings in active users / writable files / open ports
    # Flag administrators
    md.append(f"- **Privileged Accounts (Admin/Sudo):** {', '.join(sec.get('admin_users', [])) or 'None'}")
    
    # World-writable files
    unsafe_files = sec.get("world_writable_files", [])
    if unsafe_files:
        md.append("- **⚠️ Unsafe World-Writable Files detected:**")
        for f in unsafe_files:
            md.append(f"  - **CRITICAL**: `{f}` has public write permission.")
    else:
        md.append("- **World-Writable Files:** None detected (Secure)")

    # SSH keys
    keys = sec.get("ssh_keys", [])
    if keys:
        md.append(f"- **SSH Authorized Keys:** Detected {len(keys)} active key(s):")
        for k in keys:
            md.append(f"  - Key {k.get('index')}: `{k.get('comment')}` ({k.get('type')})")
    else:
        md.append("- **SSH Authorized Keys:** None found")

    return "\n".join(md)
