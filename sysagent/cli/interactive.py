import sys
import logging
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from sysagent.agent.core import GeminiAgent

console = Console()
logger = logging.getLogger("sysagent.cli.interactive")

def run_repl() -> None:
    """Starts the interactive SysAgent REPL session."""
    agent = GeminiAgent()
    
    console.print(Panel(
        "[bold green]SysAgent (Gemini) REPL Session Started.[/bold green]\n"
        "Ask questions about this machine's CPU, RAM, open ports, security audits, etc.\n"
        "Type [bold red]exit[/bold red], [bold red]quit[/bold red], or use Ctrl+C to close the session.",
        title="🤖 SysAgent System Brain",
        subtitle="Powered by Google Gemini"
    ))

    while True:
        try:
            user_input = Prompt.ask("[bold blue]SysAgent (Gemini) >[/bold blue]").strip()
            if not user_input:
                continue

            if user_input.lower() in ("exit", "quit"):
                console.print("[yellow]Closing SysAgent chat. Goodbye![/yellow]")
                break

            console.print("[dim]SysAgent is thinking...[/dim]")
            
            # Read and stream the agent response
            for chunk in agent.agentic_loop(user_input):
                # Format sandbox tool messages cleanly
                if chunk.startswith("\n*[SysAgent is running tool"):
                    console.print(chunk.strip(), style="dim yellow")
                else:
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
            print() # Print newline after response ends
            print("-" * 60)
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted. Closing chat session.[/yellow]")
            break
        except Exception as e:
            logger.error(f"REPL Session error: {e}")
            console.print(f"[bold red]Error in REPL loop: {e}[/bold red]")
            break
