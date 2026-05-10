"""`tt demo` — guided walkthrough of every feature. Zero API calls."""
import time

from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from token_tracker.analyzer.preflight import analyze
from token_tracker.dashboard.report import (
    show_analysis,
    show_cost_by_model,
    show_report,
    show_sessions,
    show_top_waste,
)

console = Console()


def _section(title: str, subtitle: str = "") -> None:
    console.print()
    console.print(Rule(f"[bold cyan]{title}[/bold cyan]", style="cyan"))
    if subtitle:
        console.print(f"[dim]{subtitle}[/dim]")
    console.print()


def _pause(seconds: float = 1.2) -> None:
    time.sleep(seconds)


def _banner() -> None:
    title = Text()
    title.append("Token Tracker", style="bold cyan")
    title.append("\n")
    title.append("Gas optimizer for LLM prompts", style="dim italic")
    console.print()
    console.print(Panel(Align.center(title), border_style="cyan", padding=(1, 4)))
    console.print()
    console.print(
        "[dim]This demo runs through every feature. No API calls are made.[/dim]"
    )


def _demo_analyze() -> None:
    _section(
        "1. Pre-flight Analyzer",
        "Score a prompt before sending. Catches waste, suggests a rewrite.",
    )

    examples = [
        (
            "BAD - heavy courtesy filler",
            "I was wondering if you could please kindly write the function and if it's not too much trouble please add docstrings",
        ),
        (
            "BAD - vague + open-ended",
            "Please could you kindly tell me something about Python and explain everything",
        ),
        (
            "GOOD - precise, scoped, formatted",
            "List the top 5 Python web frameworks as a numbered list, one line each",
        ),
    ]

    for label, prompt in examples:
        console.print(f"[bold yellow]>>>[/bold yellow] [italic]{label}[/italic]")
        console.print(f'    [dim]"{prompt}"[/dim]')
        console.print()
        result = analyze(prompt)
        show_analysis(result, original_prompt=prompt)
        _pause()


def _demo_dashboard() -> None:
    _section(
        "2. Usage Dashboard",
        "Live data from your local SQLite (~/.token_tracker/usage.db).",
    )

    console.print("[bold yellow]>>>[/bold yellow] tt report")
    console.print()
    show_report("today")
    _pause()

    console.print()
    console.print("[bold yellow]>>>[/bold yellow] tt cost-model")
    show_cost_by_model()
    _pause()

    console.print()
    console.print("[bold yellow]>>>[/bold yellow] tt top-waste")
    show_top_waste(5)
    _pause()

    console.print()
    console.print("[bold yellow]>>>[/bold yellow] tt sessions")
    console.print()
    show_sessions(10)


def _closing() -> None:
    _section("Done", "")
    msg = Text()
    msg.append("Try it on your own prompts:\n\n", style="bold")
    msg.append("  tt analyze \"<your prompt>\"\n", style="cyan")
    msg.append("  tt report\n", style="cyan")
    msg.append("  tt top-waste\n", style="cyan")
    msg.append("\nDrop ", style="")
    msg.append("TrackedClient", style="bold green")
    msg.append(" into your code to track real Claude calls automatically.\n", style="")
    console.print(Panel(msg, border_style="green", padding=(1, 2)))


def run_demo() -> None:
    _banner()
    _pause(1.5)
    _demo_analyze()
    _demo_dashboard()
    _closing()
