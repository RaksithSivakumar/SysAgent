import sys
import logging
import re
import time
import queue
import threading
from typing import Optional
from rich.console import Console, Group
from rich.prompt import Prompt
from rich.panel import Panel
from rich.live import Live
from rich.spinner import Spinner
from rich.markdown import Markdown

from sysagent.agent.core import GeminiAgent
from sysagent.config import Config
from sysagent.security.sandbox import SandboxedCollector
from sysagent.collectors import register_all_collectors

console = Console()
logger = logging.getLogger("sysagent.cli.interactive")

def show_startup_animation_and_init() -> GeminiAgent:
    """Displays a beautiful startup animation while initializing the SysAgent in a background thread."""
    if "unittest" in sys.modules or "pytest" in sys.modules:
        return GeminiAgent()
    banner = r"""   ______              ___                      __   
  / __/ /_ _____ ___ _/ _ | ___ ____ ___  ___  / /_  
 _\ \/ __/ // (_-</ _ `/ __ |/ _ `/ -_) _ \/ _ \/ __/  
/___/\__/\_, /___/\_,_/_/ |_|\_, /\__/_//_/_//_/\__/   
        /___/               /___/                      """
    console.print(Panel(banner, border_style="bold magenta", expand=False))
    console.print("[bold cyan]System Intelligence Agent[/bold cyan] | [dim]v0.1.0[/dim]\n")

    steps = [
        {"name": "Load system configuration", "status": "pending"},
        {"name": "Initialize secure sandbox", "status": "pending"},
        {"name": "Register hardware/security collectors", "status": "pending"},
        {"name": "Establish Gemini API connection", "status": "pending"}
    ]

    step_queue = queue.Queue()
    agent_container = []

    def worker():
        try:
            # Step 0: Load config
            step_queue.put((0, "running"))
            time.sleep(0.3)  # Aesthetic delay for smooth transition
            config = Config.load()
            step_queue.put((0, "success"))

            # Step 1: Init sandbox
            step_queue.put((1, "running"))
            time.sleep(0.3)
            sandbox = SandboxedCollector(config)
            step_queue.put((1, "success"))

            # Step 2: Register collectors
            step_queue.put((2, "running"))
            time.sleep(0.3)
            register_all_collectors(sandbox)
            sandbox.register_collector("get_full_report", sandbox.get_full_report)
            step_queue.put((2, "success"))

            # Step 3: Establish Gemini API
            step_queue.put((3, "running"))
            agent = GeminiAgent(config=config, sandbox=sandbox)
            if not agent.api_key:
                step_queue.put((3, "warning"))
            elif not agent.chat:
                step_queue.put((3, "failed"))
            else:
                step_queue.put((3, "success"))
            agent_container.append(agent)
        except Exception as e:
            step_queue.put(("error", str(e)))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    def get_renderable():
        group_elements = []
        for step in steps:
            if step["status"] == "pending":
                group_elements.append(f"  [dim]○[/dim] [dim]{step['name']}[/dim]")
            elif step["status"] == "running":
                group_elements.append(Spinner("dots", text=f"[bold cyan] {step['name']}...[/bold cyan]", style="bold cyan"))
            elif step["status"] == "success":
                group_elements.append(f"  [bold green]✓[/bold green] [green]{step['name']}[/green]")
            elif step["status"] == "warning":
                group_elements.append(f"  [bold yellow]⚠[/bold yellow] [yellow]{step['name']} (API Key missing/not configured)[/yellow]")
            elif step["status"] == "failed":
                group_elements.append(f"  [bold red]✗[/bold red] [red]{step['name']} (Initialization failed)[/red]")
        return Group(*group_elements)

    # Animate steps in Live display
    with Live(get_renderable(), console=console, auto_refresh=True, refresh_per_second=12) as live:
        while thread.is_alive() or not step_queue.empty():
            try:
                while True:
                    item = step_queue.get_nowait()
                    if item[0] == "error":
                        live.stop()
                        console.print(f"[bold red]Initialization Error: {item[1]}[/bold red]")
                        sys.exit(1)
                    idx, status = item
                    steps[idx]["status"] = status
                    live.update(get_renderable())
            except queue.Empty:
                pass
            time.sleep(0.05)

    console.print()
    if agent_container:
        return agent_container[0]
    else:
        return GeminiAgent()

def run_query_with_animations(agent: GeminiAgent, query: str) -> None:
    """Runs a query on the agent, displaying dynamic status spinners for tools and live-rendered markdown."""
    thinking_status = console.status("[bold cyan]SysAgent is thinking...[/bold cyan]", spinner="dots")
    thinking_status.start()
    
    active_tool_status = None
    active_tool_name = None
    tool_start_time = None
    
    live_markdown = None
    markdown_text = ""
    
    try:
        agent_iter = agent.agentic_loop(query)
        while True:
            try:
                chunk = next(agent_iter)
            except StopIteration:
                break
            
            # Stop the thinking status on first received chunk
            if thinking_status:
                thinking_status.stop()
                thinking_status = None
            
            # Check if this is a tool start chunk
            tool_match = re.match(
                r"\n\*\[SysAgent is running tool `([^`]+)`(?: with args (.*?))?\.\.\.\]\*\n", 
                chunk
            )
            
            if tool_match:
                # If a tool was previously active, close it as success
                if active_tool_status:
                    active_tool_status.stop()
                    duration = time.time() - tool_start_time
                    console.print(f"[bold green]  ✓ Ran tool:[/bold green] [cyan]{active_tool_name}[/cyan] ({duration:.2f}s)")
                
                active_tool_name = tool_match.group(1)
                args_str = tool_match.group(2) or ""
                
                # Format/truncate args for display
                display_args = f"({args_str})" if args_str else "()"
                if len(display_args) > 60:
                    display_args = display_args[:57] + "...)"
                
                active_tool_status = console.status(
                    f"[bold yellow]  🛠️  Running tool:[/bold yellow] [cyan]{active_tool_name}[/cyan][dim]{display_args}[/dim]",
                    spinner="dots"
                )
                active_tool_status.start()
                tool_start_time = time.time()
            else:
                # Text chunk received. Stop active tool status if one is running.
                if active_tool_status:
                    active_tool_status.stop()
                    duration = time.time() - tool_start_time
                    console.print(f"[bold green]  ✓ Ran tool:[/bold green] [cyan]{active_tool_name}[/cyan] ({duration:.2f}s)")
                    active_tool_status = None
                
                # Append and live render markdown
                if not live_markdown:
                    markdown_text = chunk
                    live_markdown = Live(Markdown(markdown_text), console=console, auto_refresh=True, refresh_per_second=10)
                    live_markdown.start()
                else:
                    markdown_text += chunk
                    live_markdown.update(Markdown(markdown_text))
                    
        # Loop ended, clean up any active tool/status
        if active_tool_status:
            active_tool_status.stop()
            duration = time.time() - tool_start_time
            console.print(f"[bold green]  ✓ Ran tool:[/bold green] [cyan]{active_tool_name}[/cyan] ({duration:.2f}s)")
            
        if live_markdown:
            live_markdown.stop()
            
    except Exception as e:
        if thinking_status:
            thinking_status.stop()
        if active_tool_status:
            active_tool_status.stop()
        if live_markdown:
            live_markdown.stop()
        logger.error(f"Error in run_query_with_animations: {e}")
        console.print(f"[bold red]Error querying agent: {e}[/bold red]")

def run_repl() -> None:
    """Starts the interactive SysAgent REPL session."""
    agent = show_startup_animation_and_init()
    
    console.print(Panel(
        "Ask questions about this machine's CPU, RAM, open ports, security audits, etc.\n"
        "Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to close the session.",
        title="🤖 SysAgent Session Active",
        title_align="left",
        border_style="bold green",
        expand=False
    ))

    while True:
        try:
            user_input = Prompt.ask("[bold magenta]sysagent[/bold magenta] [bold cyan]❯[/bold cyan]").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                console.print("[yellow]Closing SysAgent chat. Goodbye![/yellow]")
                break

            run_query_with_animations(agent, user_input)
            print()
            print("-" * 60)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Closing chat session.[/yellow]")
            break
        except Exception as e:
            logger.error(f"REPL Session error: {e}")
            console.print(f"[bold red]Error in REPL loop: {e}[/bold red]")
            break
