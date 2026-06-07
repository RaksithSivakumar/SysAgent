import os
import sys
import logging
from typing import Optional
import typer
from typer import Context, Typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown

# Import core configurations and managers
from sysagent.config import Config, get_api_key, set_api_key
from sysagent.security.sandbox import SandboxedCollector
from sysagent.security.encryption import encrypt_file, decrypt_report
from sysagent.collectors import register_all_collectors
from sysagent.reporters.json_report import generate_json
from sysagent.reporters.markdown_report import generate_markdown
from sysagent.reporters.html_report import generate_html
from sysagent.reporters.alert import AlertEngine
from sysagent.agent.core import GeminiAgent
from sysagent.agent.memory import save_snapshot, list_snapshots, compare_snapshots

# CLI apps
app = Typer(name="sysagent", help="AI-Powered System Intelligence Agent")
config_app = Typer(help="Manage configuration options")
history_app = Typer(help="Inspect and diff system metrics snapshots")

app.add_typer(config_app, name="config")
app.add_typer(history_app, name="history")

console = Console()
logger = logging.getLogger("sysagent.cli.commands")

def run_system_scan(config: Config) -> dict:
    """Executes all collectors securely through the sandbox."""
    sandbox = SandboxedCollector(config)
    register_all_collectors(sandbox)
    
    # Run the full report
    with console.status("[bold blue]Collecting system intelligence..."):
        report = sandbox.get_full_report()
    return report

def display_section_tables(data: dict):
    """Outputs scanned data as rich-formatted terminal tables."""
    # 1. OS & Uptime
    os_info = data.get("get_os_info", {})
    t_os = Table(title="🖥️ OS & Host Details", show_header=True, header_style="bold magenta")
    t_os.add_column("Property", style="dim")
    t_os.add_column("Value")
    t_os.add_row("Hostname", os_info.get("hostname"))
    t_os.add_row("OS Name", os_info.get("os_name"))
    t_os.add_row("OS Version", os_info.get("os_version"))
    t_os.add_row("OS Build", os_info.get("os_build"))
    t_os.add_row("Kernel Release", os_info.get("kernel_version"))
    t_os.add_row("Uptime", os_info.get("uptime_str"))
    t_os.add_row("Timezone", os_info.get("timezone"))
    t_os.add_row("Machine ID", os_info.get("machine_id"))
    console.print(t_os)
    console.print()

    # 2. CPU
    cpu = data.get("get_cpu_info", {})
    t_cpu = Table(title="⚙️ CPU Specs & Usage", show_header=True, header_style="bold blue")
    t_cpu.add_column("Specification", style="dim")
    t_cpu.add_column("Value")
    t_cpu.add_row("Model", cpu.get("model"))
    t_cpu.add_row("Architecture", cpu.get("architecture"))
    t_cpu.add_row("Cores (Physical / Logical)", f"{cpu.get('physical_cores')} / {cpu.get('logical_cores')}")
    t_cpu.add_row("Frequencies (Min/Cur/Max MHz)", f"{cpu.get('frequency_min_mhz')} / {cpu.get('frequency_current_mhz')} / {cpu.get('frequency_max_mhz')}")
    t_cpu.add_row("Overall Load", f"[bold]{cpu.get('usage_overall_pct')}%[/bold]")
    t_cpu.add_row("Temperature", f"{cpu.get('temperature_c') or 'N/A'}°C")
    t_cpu.add_row("L1d / L1i / L2 / L3 Cache", f"{cpu.get('cache_l1_data')} / {cpu.get('cache_l1_instruction')} / {cpu.get('cache_l2')} / {cpu.get('cache_l3')}")
    console.print(t_cpu)
    console.print()

    # 3. Memory
    mem = data.get("get_memory_info", {})
    ram_tot = round(mem.get("ram_total_bytes", 0) / (1024**3), 2)
    ram_usd = round(mem.get("ram_used_bytes", 0) / (1024**3), 2)
    t_mem = Table(title="💾 Memory Utilization", show_header=True, header_style="bold cyan")
    t_mem.add_column("Metric", style="dim")
    t_mem.add_column("Used / Total", style="bold")
    t_mem.add_column("Usage %")
    t_mem.add_row("RAM (Physical)", f"{ram_usd} GB / {ram_tot} GB", f"{mem.get('ram_usage_pct')}%")
    swap_tot = round(mem.get("swap_total_bytes", 0) / (1024**3), 2)
    swap_usd = round(mem.get("swap_used_bytes", 0) / (1024**3), 2)
    t_mem.add_row("Swap", f"{swap_usd} GB / {swap_tot} GB", f"{mem.get('swap_usage_pct')}%")
    t_mem.add_row("Hardware details", f"Type: {mem.get('type')} | Speed: {mem.get('speed_mhz')}", "")
    console.print(t_mem)
    console.print()

    # 4. Disks
    disk = data.get("get_disk_info", {})
    t_disk = Table(title="💽 Hard Drive Storage", show_header=True, header_style="bold green")
    t_disk.add_column("Device")
    t_disk.add_column("Mountpoint")
    t_disk.add_column("Fs Type")
    t_disk.add_column("Usage %", style="bold")
    t_disk.add_column("Capacity")
    t_disk.add_column("Free Space")
    for p in disk.get("partitions", []):
        tot = f"{round(p.get('total_bytes', 0) / (1024**3), 2)} GB"
        free = f"{round(p.get('free_bytes', 0) / (1024**3), 2)} GB"
        t_disk.add_row(p.get("device"), p.get("mountpoint"), p.get("fstype"), f"{p.get('usage_pct')}%", tot, free)
    console.print(t_disk)
    console.print(f"[dim]SMART Status: {disk.get('smart_status')}[/dim]")
    console.print()

    # 5. Network Interfaces
    net = data.get("get_network_info", {})
    t_net = Table(title="🌐 Network interfaces", show_header=True, header_style="bold yellow")
    t_net.add_column("Interface")
    t_net.add_column("Status")
    t_net.add_column("IPv4")
    t_net.add_column("MAC Address", style="dim")
    t_net.add_column("Data Sent")
    t_net.add_column("Data Recv")
    for iface in net.get("interfaces", [])[:8]: # cap to 8 interfaces in basic scan screen
        sent = f"{round(iface.get('bytes_sent', 0) / (1024**2), 1)} MB"
        recv = f"{round(iface.get('bytes_recv', 0) / (1024**2), 1)} MB"
        status = f"[green]{iface.get('status')}[/green]" if iface.get("status") == "UP" else f"[red]{iface.get('status')}[/red]"
        t_net.add_row(iface.get("name"), status, iface.get("ipv4"), iface.get("mac"), sent, recv)
    console.print(t_net)
    console.print(f"[dim]DNS servers: {', '.join(net.get('dns_servers', []))}[/dim]")
    console.print()

    # 6. Top Processes
    proc = data.get("get_processes", {})
    t_proc = Table(title="🔥 Top CPU & Memory Consumers", show_header=True, header_style="bold red")
    t_proc.add_column("PID", style="dim")
    t_proc.add_column("CPU Hog Name")
    t_proc.add_column("CPU %")
    t_proc.add_column("Memory Hog Name")
    t_proc.add_column("Memory %")
    top_cpu = proc.get("top_cpu", [])
    top_mem = proc.get("top_memory", [])
    for idx in range(min(5, len(top_cpu), len(top_mem))):
        c_p = top_cpu[idx]
        m_p = top_mem[idx]
        t_proc.add_row(
            str(c_p.get("pid")), c_p.get("name"), f"{c_p.get('cpu_pct')}%",
            m_p.get("name"), f"{m_p.get('memory_pct')}%"
        )
    console.print(t_proc)
    console.print()

@app.command()
def scan(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Report format output: json, markdown, html"),
    save: Optional[str] = typer.Option(None, "--save", "-s", help="Path to write the report file"),
    encrypt: bool = typer.Option(False, "--encrypt", "-e", help="Encrypt the output file (symmetric Fernet)")
):
    """Gathers all system telemetry, displays status, and writes reports."""
    config = Config.load()
    data = run_system_scan(config)

    # 1. Output file generator if requested
    report_content = ""
    file_format = output or (os.path.splitext(save)[1][1:] if save else None) or "terminal"
    
    if file_format == "json":
        report_content = generate_json(data, config.model)
    elif file_format == "markdown" or file_format == "md":
        report_content = generate_markdown(data)
    elif file_format == "html":
        report_content = generate_html(data)

    if save:
        if encrypt:
            encrypt_file(save, report_content or generate_json(data, config.model))
            console.print(f"[bold green]✓ Report securely encrypted and written to: {save}[/bold green]")
        else:
            with open(save, "w", encoding="utf-8") as f:
                f.write(report_content or generate_markdown(data))
            console.print(f"[bold green]✓ Report written to: {save}[/bold green]")
        # Save a snapshot to memory snapshots index automatically during standard scans
        save_snapshot(data)
        return

    # If terminal display mode
    if output == "json":
        print(generate_json(data, config.model))
    elif output in ("markdown", "md"):
        console.print(Markdown(generate_markdown(data)))
    elif output == "html":
        print(generate_html(data))
    else:
        # Default rich terminal layout display
        display_section_tables(data)

    # Always check and display alerts at the end
    engine = AlertEngine(config, data)
    alerts = engine.check_all()
    if alerts:
        console.print("[bold red]🚨 System Alerts Triggered:[/bold red]")
        for a in alerts:
            color = "red" if a.level == "CRITICAL" else "yellow"
            console.print(f"  [{color}]• {a.level}:[/{color}] {a.message}")
    else:
        console.print("[bold green]✓ All core hardware metrics are operating in safe bands.[/bold green]")

    # Save snapshot quietly
    save_snapshot(data)

@app.command()
def ask(question: str):
    """Queries Google Gemini with a system prompt and streams real-time responses."""
    agent = GeminiAgent()
    console.print(f"[dim]SysAgent is thinking using model: {agent.config.model}...[/dim]")
    
    # Run the streaming agentic loop
    for chunk in agent.agentic_loop(question):
        # We print directly to stdout to keep streaming feel
        sys.stdout.write(chunk)
        sys.stdout.flush()
    print()

@app.command()
def chat():
    """Opens an interactive REPL dialogue with Google Gemini."""
    from sysagent.cli.interactive import run_repl
    run_repl()

@app.command()
def watch():
    """Opens the live TUI hardware status dashboard (refreshes every 5s)."""
    from sysagent.cli.tui import run_tui
    run_tui()

@app.command()
def report(
    format: str = typer.Option("html", "--format", "-f", help="Output format: html, json, markdown"),
    save: str = typer.Option("./report.html", "--save", "-s", help="Output file path destination"),
    encrypt: bool = typer.Option(False, "--encrypt", "-e", help="Encrypt file with Fernet symmetric cipher")
):
    """Saves a unified system telemetry profile to disk."""
    config = Config.load()
    data = run_system_scan(config)
    
    if format == "json":
        content = generate_json(data, config.model)
    elif format == "markdown" or format == "md":
        content = generate_markdown(data)
    else:
        content = generate_html(data)

    if encrypt:
        encrypt_file(save, content)
        console.print(f"[bold green]✓ Securely encrypted {format.upper()} report written to {save}[/bold green]")
    else:
        with open(save, "w", encoding="utf-8") as f:
            f.write(content)
        console.print(f"[bold green]✓ Unified {format.upper()} report written to {save}[/bold green]")

@history_app.callback(invoke_without_command=True)
def history_main(ctx: Context):
    """Displays saved snapshots index."""
    if ctx.invoked_subcommand is None:
        snaps = list_snapshots()
        if not snaps:
            console.print("[yellow]No snapshots saved. Run `sysagent scan` to capture stats first.[/yellow]")
            return

        t_snap = Table(title="🕒 Saved Telemetry Snapshots", show_header=True, header_style="bold blue")
        t_snap.add_column("Filename", style="dim")
        t_snap.add_column("Created timestamp")
        t_snap.add_column("Full path")
        for s in snaps:
            t_snap.add_row(s.get("filename"), s.get("created"), s.get("path"))
        console.print(t_snap)

@history_app.command("diff")
def history_diff(snap1: str, snap2: str):
    """Compares metrics between two telemetry snapshot files."""
    snap_dir = os.path.join(os.path.expanduser("~"), ".sysagent", "snapshots")
    
    # Resolve short names to actual paths if needed
    p1 = snap1 if os.path.exists(snap1) else os.path.join(snap_dir, snap1)
    p2 = snap2 if os.path.exists(snap2) else os.path.join(snap_dir, snap2)

    if not os.path.exists(p1) or not os.path.exists(p2):
        console.print("[bold red]Error: One or both snapshot files do not exist.[/bold red]")
        return

    diffs = compare_snapshots(p1, p2)
    if "error" in diffs:
        console.print(f"[bold red]Comparison failed: {diffs['error']}[/bold red]")
        return

    console.print(Panel(
        f"[bold blue]Comparing snapshot 1 ({os.path.basename(p1)}) vs snapshot 2 ({os.path.basename(p2)})[/bold blue]\n"
        f"  [bold]Timeline delta:[/bold] {diffs.get('uptime_change_str', 'N/A')}\n"
        f"  [bold]CPU load diff:[/bold] {diffs.get('cpu_usage_change_pct', 0)}%\n"
        f"  [bold]Memory load diff:[/bold] {diffs.get('ram_usage_change_pct', 0)}%\n"
        f"  [bold]New Listening Ports:[/bold] {', '.join(map(str, diffs.get('new_exposed_ports', []))) or 'None'}\n"
        f"  [bold]Closed Ports:[/bold] {', '.join(map(str, diffs.get('closed_exposed_ports', []))) or 'None'}\n"
        f"  [bold]Spawned Processes:[/bold] {', '.join(diffs.get('new_processes', []))[:150] or 'None'}\n"
        f"  [bold]Killed Processes:[/bold] {', '.join(diffs.get('terminated_processes', []))[:150] or 'None'}",
        title="🕵️ Telemetry Diff results"
    ))

@config_app.callback(invoke_without_command=True)
def config_main(ctx: Context):
    """Displays active configuration parameters (GEMINI_API_KEY is masked)."""
    if ctx.invoked_subcommand is None:
        c = Config.load()
        key = get_api_key()
        masked_key = f"{key[:6]}...{key[-4:]}" if key else "NOT CONFIGURED"
        
        t_conf = Table(title="⚙️ SysAgent Configuration Settings", show_header=True, header_style="bold green")
        t_conf.add_column("Parameter", style="dim")
        t_conf.add_column("Active value")
        t_conf.add_row("Gemini Model", str(c.model))
        t_conf.add_row("Read Only Mode", str(c.read_only_mode))
        t_conf.add_row("Cache TTL Seconds", f"{c.cache_ttl_seconds}s")
        t_conf.add_row("Log Level", str(c.log_level))
        t_conf.add_row("Max History Turns", str(c.max_history_turns))
        t_conf.add_row("Alert CPU Threshold %", f"{c.cpu_usage_pct}%")
        t_conf.add_row("Alert Memory Threshold %", f"{c.memory_usage_pct}%")
        t_conf.add_row("Alert Disk Threshold %", f"{c.disk_usage_pct}%")
        t_conf.add_row("Alert Battery Threshold %", f"{c.battery_pct}%")
        t_conf.add_row("GEMINI_API_KEY", masked_key)
        
        console.print(t_conf)

@config_app.command("set")
def config_set(key: str, value: str):
    """Configures setting values (stored in config.toml or secure keyring)."""
    c = Config.load()
    key_upper = key.upper()

    if key_upper == "GEMINI_API_KEY":
        if set_api_key(value):
            console.print("[bold green]✓ GEMINI_API_KEY stored securely in keyring database.[/bold green]")
        else:
            console.print("[bold red]Failed to write GEMINI_API_KEY to system keyring database.[/bold red]")
        return

    # Check alert threshold fields
    if key in ("alert.cpu_threshold", "cpu_usage_pct"):
        c.cpu_usage_pct = float(value)
    elif key in ("alert.memory_threshold", "memory_usage_pct"):
        c.memory_usage_pct = float(value)
    elif key in ("alert.disk_threshold", "disk_usage_pct"):
        c.disk_usage_pct = float(value)
    elif key in ("alert.battery_threshold", "battery_pct"):
        c.battery_pct = float(value)
    elif key == "model":
        c.model = value
    elif key == "read_only_mode":
        c.read_only_mode = (value.lower() == "true")
    elif key == "cache_ttl_seconds":
        c.cache_ttl_seconds = int(value)
    elif key == "log_level":
        c.log_level = value
    elif key == "max_history_turns":
        c.max_history_turns = int(value)
    else:
        console.print(f"[bold red]Unknown parameter name: {key}[/bold red]")
        return

    c.save()
    console.print(f"[bold green]✓ Setting '{key}' updated to: {value}[/bold green]")
