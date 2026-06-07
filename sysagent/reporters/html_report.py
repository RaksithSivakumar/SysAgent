import socket
from datetime import datetime
from typing import Dict, Any

def generate_html(data: Dict[str, Any]) -> str:
    """Generates a premium-grade single-file HTML dashboard report with modern dark styling."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    hostname = data.get("get_os_info", {}).get("hostname") or socket.gethostname()
    
    os_info = data.get("get_os_info", {})
    cpu = data.get("get_cpu_info", {})
    mem = data.get("get_memory_info", {})
    disk = data.get("get_disk_info", {})
    gpu = data.get("get_gpu_info", {})
    net = data.get("get_network_info", {})
    proc = data.get("get_processes", {})
    soft = data.get("get_software_info", {})
    sec = data.get("get_security_audit", {})

    # Helper function to get color based on usage percent
    def get_progress_color(pct: float) -> str:
        if pct < 60.0:
            return "#10b981" # Green
        elif pct < 85.0:
            return "#f59e0b" # Amber
        else:
            return "#ef4444" # Red

    # Calc GB values
    ram_tot = round(mem.get("ram_total_bytes", 0) / (1024**3), 2)
    ram_usd = round(mem.get("ram_used_bytes", 0) / (1024**3), 2)
    ram_pct = mem.get("ram_usage_pct", 0.0)
    ram_color = get_progress_color(ram_pct)

    cpu_pct = cpu.get("usage_overall_pct", 0.0)
    cpu_color = get_progress_color(cpu_pct)

    # Process partitions for HTML
    partitions_html = []
    for part in disk.get("partitions", []):
        tot_gb = round(part.get("total_bytes", 0) / (1024**3), 2)
        free_gb = round(part.get("free_bytes", 0) / (1024**3), 2)
        used_pct = part.get("usage_pct", 0.0)
        color = get_progress_color(used_pct)
        partitions_html.append(f"""
        <tr>
            <td><code>{part.get('device')}</code></td>
            <td><code>{part.get('mountpoint')}</code></td>
            <td>{part.get('fstype')}</td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {used_pct}%; background: {color};"></div>
                    <span class="progress-text">{used_pct}%</span>
                </div>
            </td>
            <td>{tot_gb} GB</td>
            <td>{free_gb} GB</td>
        </tr>
        """)
    partitions_str = "\n".join(partitions_html)

    # Process interfaces
    net_html = []
    for iface in net.get("interfaces", []):
        tx_mb = round(iface.get("bytes_sent", 0) / (1024**2), 2)
        rx_mb = round(iface.get("bytes_recv", 0) / (1024**2), 2)
        status_class = "badge-success" if iface.get("status") == "UP" else "badge-danger"
        net_html.append(f"""
        <tr>
            <td><strong>{iface.get('name')}</strong></td>
            <td><span class="badge {status_class}">{iface.get('status')}</span></td>
            <td>{iface.get('ipv4')}</td>
            <td><code>{iface.get('mac')}</code></td>
            <td>{tx_mb} MB</td>
            <td>{rx_mb} MB</td>
        </tr>
        """)
    net_str = "\n".join(net_html)

    # Top CPU
    cpu_proc_html = []
    for p in proc.get("top_cpu", [])[:5]:
        cpu_proc_html.append(f"""
        <tr>
            <td>{p.get('pid')}</td>
            <td><code>{p.get('name')}</code></td>
            <td style="color: #ef4444; font-weight: 600;">{p.get('cpu_pct')}%</td>
            <td>{p.get('memory_pct')}%</td>
        </tr>
        """)
    cpu_proc_str = "\n".join(cpu_proc_html)

    # Top Memory
    mem_proc_html = []
    for p in proc.get("top_memory", [])[:5]:
        mem_proc_html.append(f"""
        <tr>
            <td>{p.get('pid')}</td>
            <td><code>{p.get('name')}</code></td>
            <td style="color: #f59e0b; font-weight: 600;">{p.get('memory_pct')}%</td>
            <td>{p.get('cpu_pct')}%</td>
        </tr>
        """)
    mem_proc_str = "\n".join(mem_proc_html)

    # Dev Runtimes
    dev_tools = soft.get("dev_tools", {})
    tools_html = []
    for tool, ver in dev_tools.items():
        tools_html.append(f"<li><strong>{tool.capitalize()}:</strong> {ver}</li>")
    tools_str = "\n".join(tools_html)

    # World writable files
    unsafe_files = sec.get("world_writable_files", [])
    security_alerts_html = []
    if unsafe_files:
        for f in unsafe_files:
            security_alerts_html.append(f"""
            <div class="alert-box alert-critical">
                <strong>CRITICAL:</strong> World-writable file found: <code>{f}</code>
            </div>
            """)
    
    # Listening ports warning
    ports = sec.get("listening_ports", []) # Wait, firewall details contains listening ports exposed
    firewall_det = data.get("get_firewall_info", {})
    listening_ports = firewall_det.get("listening_ports", [])
    for p in listening_ports:
        if p.get("exposed_warning"):
            security_alerts_html.append(f"""
            <div class="alert-box alert-warning">
                <strong>WARNING:</strong> Exposed port <code>{p.get('port')}</code> ({p.get('proto')}) listening on <code>{p.get('address')}</code> (Not 80/443).
            </div>
            """)

    if not security_alerts_html:
        security_alerts_html.append("""
        <div class="alert-box alert-success">
            <strong>SECURE:</strong> No critical vulnerabilities, exposed ports, or world-writable files identified.
        </div>
        """)
    security_alerts_str = "\n".join(security_alerts_html)

    # Battery
    bat = data.get("get_battery_info", {})
    battery_block = ""
    if bat.get("present"):
        bat_color = get_progress_color(bat.get("charge_pct", 0.0))
        battery_block = f"""
        <div class="card">
            <h3>🔋 Battery Status</h3>
            <div class="metric-row">
                <span class="metric-label">Charge level</span>
                <span class="metric-value">{bat.get('charge_pct')}%</span>
            </div>
            <div class="progress-container" style="margin-bottom: 15px;">
                <div class="progress-bar" style="width: {bat.get('charge_pct')}%; background: {bat_color};"></div>
            </div>
            <p><strong>Status:</strong> {bat.get('status')} | <strong>Time remaining:</strong> {bat.get('time_remaining_str')}</p>
            <p><strong>Cycles:</strong> {bat.get('cycle_count')}</p>
        </div>
        """

    # GPU
    gpu_blocks = []
    if gpu.get("gpu_detected"):
        for g in gpu.get("gpus", []):
            gpu_blocks.append(f"""
            <div class="card">
                <h3>🎮 Graphics Processor (GPU)</h3>
                <h4 style="margin: 5px 0 15px 0; color: #60a5fa;">{g.get('name')}</h4>
                <div class="metric-row"><span>Vendor</span><span>{g.get('vendor')}</span></div>
                <div class="metric-row"><span>Driver Version</span><span>{g.get('driver_version')}</span></div>
                <div class="metric-row"><span>VRAM Total</span><span>{g.get('vram_total_mb')} MB</span></div>
                <div class="metric-row"><span>VRAM Used</span><span>{g.get('vram_used_mb')} MB</span></div>
                <div class="metric-row"><span>Temperature</span><span>{g.get('temperature_c')}°C</span></div>
                <div class="metric-row"><span>GPU Load</span><span>{g.get('load_pct')}%</span></div>
            </div>
            """)
    gpu_str = "\n".join(gpu_blocks)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SysAgent Dashboard - {hostname}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
        
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 29, 49, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-main: #f3f4f6;
            --text-secondary: #9ca3af;
            --primary: #3b82f6;
            --primary-glow: rgba(59, 130, 246, 0.35);
        }}

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            background-color: var(--bg-color);
            background-image: radial-gradient(circle at 10% 20%, rgba(20, 30, 60, 0.6) 0%, rgba(10, 15, 25, 0.9) 80%);
            color: var(--text-main);
            font-family: 'Outfit', sans-serif;
            line-height: 1.6;
            padding: 40px 20px;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        /* Header section */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 25px;
            margin-bottom: 35px;
        }}

        .brand h1 {{
            font-size: 2.2rem;
            font-weight: 800;
            background: linear-gradient(135deg, #60a5fa 30%, #3b82f6 90%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -0.5px;
        }}

        .brand p {{
            color: var(--text-secondary);
            font-size: 0.95rem;
            margin-top: 4px;
        }}

        .status-badge {{
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid #10b981;
            color: #10b981;
            padding: 6px 14px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .status-dot {{
            width: 8px;
            height: 8px;
            background-color: #10b981;
            border-radius: 50%;
            display: inline-block;
            box-shadow: 0 0 8px #10b981;
            animation: pulse 2s infinite;
        }}

        @keyframes pulse {{
            0% {{ transform: scale(0.95); opacity: 0.5; }}
            50% {{ transform: scale(1.1); opacity: 1; }}
            100% {{ transform: scale(0.95); opacity: 0.5; }}
        }}

        /* Grid layouts */
        .grid-3 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 25px;
            margin-bottom: 35px;
        }}

        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 25px;
            margin-bottom: 35px;
        }}

        /* Card stylings */
        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }}

        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 15px 30px rgba(59, 130, 246, 0.1);
            border-color: rgba(59, 130, 246, 0.2);
        }}

        .card h3 {{
            font-size: 1.25rem;
            font-weight: 700;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            padding-bottom: 10px;
        }}

        /* Metrics key-value rows */
        .metric-row {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.03);
            font-size: 0.95rem;
        }}

        .metric-row:last-child {{
            border-bottom: none;
        }}

        .metric-label {{
            color: var(--text-secondary);
        }}

        .metric-value {{
            font-weight: 600;
            color: var(--text-main);
        }}

        /* Progress bars */
        .progress-container {{
            background: rgba(255, 255, 255, 0.05);
            height: 16px;
            border-radius: 8px;
            position: relative;
            overflow: hidden;
            margin-top: 8px;
        }}

        .progress-bar {{
            height: 100%;
            border-radius: 8px;
            transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }}

        .progress-text {{
            position: absolute;
            right: 10px;
            top: 50%;
            transform: translateY(-50%);
            font-size: 0.75rem;
            font-weight: 700;
            color: #ffffff;
            text-shadow: 0 1px 2px rgba(0,0,0,0.8);
        }}

        /* Tables styling */
        .table-card {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }}

        th {{
            color: var(--text-secondary);
            font-weight: 600;
            padding: 12px;
            border-bottom: 2px solid rgba(255, 255, 255, 0.08);
        }}

        td {{
            padding: 14px 12px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            color: var(--text-main);
        }}

        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}

        code {{
            background: rgba(0, 0, 0, 0.3);
            padding: 3px 6px;
            border-radius: 4px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 0.85rem;
            color: #60a5fa;
        }}

        /* Badges */
        .badge {{
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 600;
        }}

        .badge-success {{
            background: rgba(16, 185, 129, 0.15);
            color: #10b981;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}

        .badge-danger {{
            background: rgba(239, 68, 68, 0.15);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}

        .badge-warning {{
            background: rgba(245, 158, 11, 0.15);
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}

        /* Alerts engine styling */
        .alert-box {{
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 12px;
            font-size: 0.95rem;
            display: flex;
            align-items: center;
        }}

        .alert-critical {{
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #fca5a5;
        }}

        .alert-warning {{
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            color: #fde047;
        }}

        .alert-success {{
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #a7f3d0;
        }}

        ul {{
            list-style-position: inside;
            color: var(--text-main);
            padding-left: 10px;
        }}

        li {{
            margin-bottom: 8px;
            font-size: 0.95rem;
        }}

        footer {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
            border-top: 1px solid var(--border-color);
            padding-top: 25px;
            margin-top: 50px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="brand">
                <h1>SysAgent Dashboard</h1>
                <p>Host: {hostname} | OS: {os_info.get('os_name')} | Uptime: {os_info.get('uptime_str')}</p>
            </div>
            <div class="status-badge">
                <span class="status-dot"></span> SECURE MODE
            </div>
        </header>

        <!-- System overview metrics (Gauge cards) -->
        <div class="grid-3">
            <!-- CPU Card -->
            <div class="card">
                <h3>🖥️ CPU Utilization</h3>
                <div class="metric-row">
                    <span class="metric-label">Model</span>
                    <span class="metric-value" style="font-size:0.85rem; text-align:right; max-width:70%;">{cpu.get('model')}</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Cores</span>
                    <span class="metric-value">{cpu.get('physical_cores')} Cores ({cpu.get('logical_cores')} Logical)</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Total Load</span>
                    <span class="metric-value" style="color:{cpu_color};">{cpu_pct}%</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {cpu_pct}%; background: {cpu_color};"></div>
                    <span class="progress-text">{cpu_pct}%</span>
                </div>
            </div>

            <!-- Memory Card -->
            <div class="card">
                <h3>💾 System RAM</h3>
                <div class="metric-row">
                    <span class="metric-label">Total Memory</span>
                    <span class="metric-value">{ram_tot} GB</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Used RAM</span>
                    <span class="metric-value">{ram_usd} GB</span>
                </div>
                <div class="metric-row">
                    <span class="metric-label">Usage Percentage</span>
                    <span class="metric-value" style="color:{ram_color};">{ram_pct}%</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {ram_pct}%; background: {ram_color};"></div>
                    <span class="progress-text">{ram_pct}%</span>
                </div>
            </div>

            <!-- Operating System Card -->
            <div class="card">
                <h3>⚙️ System details</h3>
                <div class="metric-row"><span>OS Architecture</span><span>{cpu.get('architecture')}</span></div>
                <div class="metric-row"><span>OS Build</span><span style="font-size:0.8rem;">{os_info.get('os_build')}</span></div>
                <div class="metric-row"><span>Kernel Version</span><span style="font-size:0.8rem;">{os_info.get('kernel_version')}</span></div>
                <div class="metric-row"><span>Timezone</span><span>{os_info.get('timezone')}</span></div>
            </div>
        </div>

        <!-- GPU & Battery Row (if active) -->
        <div class="grid-2">
            {gpu_str}
            {battery_block}
        </div>

        <!-- Storage & Disks -->
        <div class="card table-card" style="margin-bottom: 35px;">
            <h3>💽 Hard Drive Partitions & Mountpoints</h3>
            <table>
                <thead>
                    <tr>
                        <th>Device</th>
                        <th>Mountpoint</th>
                        <th>File System</th>
                        <th>Used %</th>
                        <th>Capacity</th>
                        <th>Free Space</th>
                    </tr>
                </thead>
                <tbody>
                    {partitions_str}
                </tbody>
            </table>
            <div class="metric-row" style="margin-top: 15px; border:none; padding: 0;">
                <span class="metric-label"><strong>SMART Hardware Status:</strong></span>
                <span class="metric-value" style="color: #60a5fa;">{disk.get('smart_status')}</span>
            </div>
        </div>

        <!-- Security alerts box -->
        <div class="grid-2">
            <div class="card">
                <h3>🛡️ Security Audit & Threat Center</h3>
                {security_alerts_str}
                <div style="margin-top: 20px;">
                    <p style="font-size: 0.9rem; color: var(--text-secondary);">
                        <strong>Local Admins:</strong> {", ".join(sec.get('admin_users', []))}
                    </p>
                </div>
            </div>

            <div class="card">
                <h3>📦 Software & Build Environment</h3>
                <div class="metric-row"><span>Python Runtime</span><span>{soft.get('python_version')}</span></div>
                <div class="metric-row"><span>Active Virtualenv</span><span><code>{soft.get('virtualenv')}</code></span></div>
                <div class="metric-row"><span>Git Version</span><span>{soft.get('git_version')}</span></div>
                <h4 style="margin: 15px 0 10px 0; font-size: 1rem;">Developer tools versions:</h4>
                <ul style="margin-bottom: 15px;">
                    {tools_str}
                </ul>
            </div>
        </div>

        <!-- Network Adaptors and Traffic -->
        <div class="card table-card" style="margin-bottom: 35px;">
            <h3>🌐 Network Adapters & Configurations</h3>
            <table>
                <thead>
                    <tr>
                        <th>Interface Name</th>
                        <th>Status</th>
                        <th>IP Address</th>
                        <th>MAC Address</th>
                        <th>Data Sent</th>
                        <th>Data Received</th>
                    </tr>
                </thead>
                <tbody>
                    {net_str}
                </tbody>
            </table>
            <div class="metric-row" style="margin-top: 15px; border:none; padding: 0;">
                <span class="metric-label"><strong>DNS Servers Configured:</strong></span>
                <span class="metric-value">{", ".join(net.get('dns_servers', []))}</span>
            </div>
        </div>

        <!-- Processes Cards -->
        <div class="grid-2">
            <!-- Top CPU -->
            <div class="card table-card">
                <h3>🔥 Top 5 CPU Processes</h3>
                <table>
                    <thead>
                        <tr>
                            <th>PID</th>
                            <th>Process Name</th>
                            <th>CPU %</th>
                            <th>Memory %</th>
                        </tr>
                    </thead>
                    <tbody>
                        {cpu_proc_str}
                    </tbody>
                </table>
            </div>

            <!-- Top Memory -->
            <div class="card table-card">
                <h3>💡 Top 5 Memory Processes</h3>
                <table>
                    <thead>
                        <tr>
                            <th>PID</th>
                            <th>Process Name</th>
                            <th>Memory %</th>
                            <th>CPU %</th>
                        </tr>
                    </thead>
                    <tbody>
                        {mem_proc_str}
                    </tbody>
                </table>
            </div>
        </div>

        <footer>
            <p>Generated by SysAgent - AI System Intelligence Assistant. Local and Sandboxed execution model.</p>
        </footer>
    </div>
</body>
</html>
"""
    return html
