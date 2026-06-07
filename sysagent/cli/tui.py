import os
import sys
import time
import socket
from datetime import datetime
from typing import Dict, Any, List

from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.console import Console, Group
from rich.progress import Progress, BarColumn, TextColumn

from sysagent.config import Config
from sysagent.utils.platform_detect import get_platform
from sysagent.collectors.cpu import get_cpu_info
from sysagent.collectors.memory import get_memory_info
from sysagent.collectors.disk import get_disk_info
from sysagent.collectors.processes import get_processes
from sysagent.collectors.os_info import get_os_info
from sysagent.collectors.battery import get_battery_info
from sysagent.collectors.network import get_network_info
from sysagent.security.firewall import get_firewall_info
from sysagent.security.audit import get_security_audit
from sysagent.reporters.alert import AlertEngine

console = Console()

def get_progress_bar_color(pct: float) -> str:
    if pct < 60.0:
        return "green"
    elif pct < 85.0:
        return "yellow"
    else:
        return "red"

def check_quit_key() -> bool:
    """Checks for non-blocking console key input to exit TUI loop ('q' or 'Q')."""
    plat = get_platform()
    if plat == "windows":
        try:
            import msvcrt
            if msvcrt.kbhit():
                ch = msvcrt.getch()
                if ch.lower() in (b"q", b"\x03"): # q or Ctrl+C
                    return True
        except Exception:
            pass
    else:
        try:
            import select
            import tty
            import termios
            fd = sys.stdin.fileno()
            if os.isatty(fd):
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if rlist:
                        ch = sys.stdin.read(1)
                        if ch.lower() in ("q", "\x03"):
                            return True
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except Exception:
            pass
    return False

def make_layout() -> Layout:
    """Creates the structural grid for the TUI."""
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    
    layout["body"].split_row(
        Layout(name="metrics", ratio=2),
        Layout(name="processes", ratio=3)
    )
    
    layout["metrics"].split_column(
        Layout(name="cpu"),
        Layout(name="ram"),
        Layout(name="disk")
    )
    
    return layout

def update_tui_layout(layout: Layout, config: Config) -> None:
    """Pulls current hardware metrics and populates the layout objects."""
    # Gather live data (bypass cache by calling directly)
    cpu = get_cpu_info()
    mem = get_memory_info()
    disk = get_disk_info()
    proc = get_processes()
    os_info = get_os_info()
    bat = get_battery_info()
    net = get_network_info()
    firewall_info = get_firewall_info()
    sec_audit = get_security_audit()

    # Compile unified dictionary for the AlertEngine
    unified_data = {
        "get_cpu_info": cpu,
        "get_memory_info": mem,
        "get_disk_info": disk,
        "get_processes": proc,
        "get_os_info": os_info,
        "get_battery_info": bat,
        "get_network_info": net,
        "get_firewall_info": firewall_info,
        "get_security_audit": sec_audit
    }

    # Run AlertEngine
    alerts = AlertEngine(config, unified_data).check_all()

    # Header Panel
    hostname = socket.gethostname()
    os_str = f"{os_info.get('os_name')} {os_info.get('os_version')} (Kernel: {os_info.get('kernel_version')})"
    uptime = os_info.get("uptime_str", "Calculating...")
    bat_str = f" | Battery: {bat.get('charge_pct')}% ({bat.get('status')})" if bat.get("present") else ""
    
    layout["header"].update(Panel(
        f"[bold cyan]Host:[/] {hostname} | [bold cyan]OS:[/] {os_str} | [bold cyan]Uptime:[/] {uptime}{bat_str}",
        title="🖥️ SysAgent Live Monitor",
        border_style="blue"
    ))

    # CPU Panel
    cpu_pct = cpu.get("usage_overall_pct", 0.0)
    cpu_color = get_progress_bar_color(cpu_pct)
    
    # Progress rendering
    progress_cpu = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=25),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    progress_cpu.add_task(f"CPU Load", total=100, completed=cpu_pct)
    
    temp_str = f" | Temp: {cpu.get('temperature_c')}°C" if cpu.get("temperature_c") else ""
    layout["cpu"].update(Panel(
        Group(
            f"[dim]{cpu.get('model')}[/dim]\n"
            f"Cores: {cpu.get('physical_cores')} Physical / {cpu.get('logical_cores')} Logical{temp_str}\n"
            f"Freq: {cpu.get('frequency_current_mhz')} MHz\n",
            progress_cpu.make_tasks_table(progress_cpu.tasks)
        ),
        title="⚙️ CPU Usage",
        border_style=cpu_color
    ))

    # RAM Panel
    ram_pct = mem.get("ram_usage_pct", 0.0)
    ram_color = get_progress_bar_color(ram_pct)
    ram_tot = round(mem.get("ram_total_bytes", 0) / (1024**3), 2)
    ram_usd = round(mem.get("ram_used_bytes", 0) / (1024**3), 2)
    
    progress_ram = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=25),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    )
    progress_ram.add_task("RAM Load", total=100, completed=ram_pct)
    
    layout["ram"].update(Panel(
        Group(
            f"Total RAM: {ram_tot} GB | Used: {ram_usd} GB\n"
            f"Speed/Type: {mem.get('speed_mhz')} / {mem.get('type')}\n",
            progress_ram.make_tasks_table(progress_ram.tasks)
        ),
        title="💾 Memory usage",
        border_style=ram_color
    ))

    # Disk Panel
    disk_p = disk.get("partitions", [])
    disk_text = []
    for p in disk_p[:3]: # display top 3 disk partition rows
        used_pct = p.get("usage_pct", 0.0)
        color = get_progress_bar_color(used_pct)
        disk_text.append(f"{p.get('mountpoint')} ({p.get('fstype')}): [{color}]{used_pct}%[/{color}] of {round(p.get('total_bytes',0)/(1024**3),1)} GB")
    
    layout["disk"].update(Panel(
        "\n".join(disk_text) or "No drives detected.",
        title="💽 Storage / Partitions",
        border_style="green"
    ))

    # Processes Panel
    top_proc = proc.get("top_cpu", [])[:8] # show top 8 processes
    p_table = Table(show_header=True, header_style="bold red", expand=True)
    p_table.add_column("PID", width=6)
    p_table.add_column("Process Name")
    p_table.add_column("CPU %", justify="right")
    p_table.add_column("RAM %", justify="right")
    
    for p in top_proc:
        p_table.add_row(
            str(p.get("pid")),
            p.get("name"),
            f"{p.get('cpu_pct')}%",
            f"{p.get('memory_pct')}%"
        )
        
    layout["processes"].update(Panel(
        p_table,
        title="🔥 Top Processes (by CPU)",
        border_style="red"
    ))

    # Footer Panel (Show active alerts or exit help)
    if alerts:
        alert_strs = []
        for a in alerts[:2]: # fit max 2 alert strings in footer panel
            color = "red" if a.level == "CRITICAL" else "yellow"
            alert_strs.append(f"[{color}]{a.level}:[/] {a.message}")
        alert_text = " | ".join(alert_strs)
        layout["footer"].update(Panel(
            f"[bold red]WARNING:[/] {alert_text}  [dim](Press Q to quit, refreshed every 5s)[/dim]",
            border_style="yellow"
        ))
    else:
        layout["footer"].update(Panel(
            "[bold green]✓ System metrics are stable.[/bold green] Press [bold cyan]Q[/bold cyan] to exit monitoring dashboard. [dim]Refreshed every 5s[/dim]",
            border_style="green"
        ))

def run_tui() -> None:
    """Starts the TUI watch rendering thread loop."""
    config = Config.load()
    layout = make_layout()

    console.print("[dim]Initializing watch dashboard...[/dim]")
    
    with Live(layout, refresh_per_second=2, screen=True) as live:
        while True:
            # Update metrics
            update_tui_layout(layout, config)
            
            # Check keyboard input every 100ms for 5 seconds to respond instantly to Q
            for _ in range(50):
                if check_quit_key():
                    return
                time.sleep(0.1)
