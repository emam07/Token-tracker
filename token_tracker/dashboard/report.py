from datetime import datetime

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from token_tracker.core.tracker import _DEFAULT_COSTS, MODEL_COSTS, _normalize_model
from token_tracker.storage.db import (
    get_cache_savings,
    get_cost_by_model,
    get_sessions,
    get_top_waste,
    get_usage_range,
    get_usage_today,
)

console = Console()

_SEVERITY_COLOR = {"high": "red", "medium": "yellow", "low": "cyan"}
_SEVERITY_ICON  = {"high": "[!]", "medium": "[~]", "low": "[-]"}


def _short_model(name: str) -> str:
    if not name:
        return "-"
    # strip trailing date suffix like "-20251001"
    import re
    return re.sub(r"-\d{8}$", "", name)


def show_analysis(analysis, original_prompt: str = "") -> None:
    from token_tracker.analyzer.scorer import score_label

    label, color = score_label(analysis.efficiency_score)

    header = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    header.add_column("k", style="bold cyan", no_wrap=True)
    header.add_column("v", justify="right")
    header.add_row("Estimated tokens", f"{analysis.estimated_input_tokens:,}")
    header.add_row("Estimated cost",   f"${analysis.estimated_cost_usd:.6f}")
    header.add_row(
        "Efficiency score",
        f"[{color}]{analysis.efficiency_score} / 100  {label}[/{color}]",
    )

    console.print(Panel(header, title="[bold]Pre-flight Analysis[/bold]", border_style=color))

    if not analysis.warnings:
        console.print("[green]  No issues found.[/green]\n")
        return

    console.print(f"  [bold]Warnings ({len(analysis.warnings)}):[/bold]")
    for w in analysis.warnings:
        c = _SEVERITY_COLOR.get(w.severity, "white")
        icon = _SEVERITY_ICON.get(w.severity, "*")
        console.print(f"  [{c}]{icon} {w.severity.upper():6}[/{c}]  [bold]{w.rule}[/bold]")
        console.print(f"         {w.message}")
        console.print(f"         [dim]> {w.suggestion}[/dim]")
    console.print()

    if analysis.suggested_rewrite:
        _show_rewrite_diff(
            original=original_prompt,
            rewrite=analysis.suggested_rewrite,
            token_delta=analysis.token_delta,
        )


def _show_rewrite_diff(original, rewrite, token_delta):
    if token_delta > 0:
        delta_text = f"[green]-{token_delta} tokens[/green]"
    elif token_delta < 0:
        delta_text = f"[yellow]+{-token_delta} tokens (added constraints)[/yellow]"
    else:
        delta_text = "[dim]same length[/dim]"

    diff_table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1), expand=True)
    diff_table.add_column("Original",  style="dim",   ratio=1)
    diff_table.add_column("Optimized", style="green", ratio=1)
    diff_table.add_row(original or "[see prompt above]", rewrite)

    console.print(Panel(
        diff_table,
        title=f"[bold]Suggested Rewrite[/bold]  ({delta_text})",
        border_style="green",
    ))


def _fmt_tokens(n) -> str:
    return f"{int(n or 0):,}"


def _fmt_cost(n) -> str:
    return f"${float(n or 0):.4f}"


def _fmt_score(n) -> str:
    if n is None:
        return "[dim]-[/dim]"
    score = int(n)
    if score >= 80:
        return f"[green]{score} / 100[/green]"
    if score >= 60:
        return f"[yellow]{score} / 100[/yellow]"
    return f"[red]{score} / 100[/red]"


def _fmt_score_compact(n) -> str:
    if n is None:
        return "[dim]-[/dim]"
    score = int(n)
    color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
    return f"[{color}]{score}[/{color}]"


def show_report(period: str = "today") -> None:
    if period == "today":
        row = get_usage_today()
        title = f"Token Usage — Today ({datetime.utcnow().date()})"
    elif period == "week":
        row = get_usage_range(7)
        title = "Token Usage — Last 7 Days"
    else:
        row = get_usage_range(30)
        title = "Token Usage — Last 30 Days"

    if not row or row["requests"] == 0:
        console.print(f"[dim]No usage data for {period}.[/dim]")
        return

    # Compute cache savings using the actual per-model input vs cache_read rates
    cache_saved = sum(
        (r["cache_read_tokens"] or 0)
        * (
            MODEL_COSTS.get(_normalize_model(r["model"] or ""), _DEFAULT_COSTS)["input"]
            - MODEL_COSTS.get(_normalize_model(r["model"] or ""), _DEFAULT_COSTS)["cache_read"]
        )
        / 1_000_000
        for r in get_cache_savings(period)
    )

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="bold cyan", no_wrap=True)
    table.add_column("Value", justify="right")

    table.add_row("Requests",           str(row["requests"]))
    table.add_row("Input tokens",       _fmt_tokens(row["input_tokens"]))
    table.add_row("Output tokens",      _fmt_tokens(row["output_tokens"]))
    table.add_row(
        "Cache read tokens",
        _fmt_tokens(row["cache_read_tokens"])
        + f"  [dim](saved ~{_fmt_cost(cache_saved)})[/dim]",
    )
    table.add_row("Total cost",         _fmt_cost(row["cost_usd"]))
    table.add_row("Avg efficiency",     _fmt_score(row["avg_efficiency"]))

    if row["flagged_count"]:
        table.add_row(
            "Flagged prompts",
            f"[yellow]{int(row['flagged_count'])}[/yellow]",
        )

    console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style="blue"))


def show_sessions(limit: int = 20) -> None:
    rows = get_sessions(limit)
    if not rows:
        console.print("[dim]No sessions found.[/dim]")
        return

    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 2))
    table.add_column("Session ID",  style="dim", no_wrap=True)
    table.add_column("Name",        style="cyan")
    table.add_column("Started",     justify="right")

    for r in rows:
        started = r["started_at"][:19].replace("T", " ")
        table.add_row(r["id"][:8] + "...", r["name"] or "-", started)

    console.print(Panel(table, title="[bold]Sessions[/bold]", border_style="blue"))


def show_top_waste(limit: int = 10) -> None:
    rows = get_top_waste(limit)
    if not rows:
        console.print("[dim]No flagged prompts in the last 30 days.[/dim]")
        return

    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 1))
    table.add_column("When",        style="dim",  no_wrap=True)
    table.add_column("Model",       style="cyan", no_wrap=True)
    table.add_column("Score",       justify="right", no_wrap=True)
    table.add_column("In+Out",      justify="right", no_wrap=True)
    table.add_column("Cost",        justify="right", no_wrap=True, style="bold red")

    for r in rows:
        when = r["timestamp"][:16].replace("T", " ")
        table.add_row(
            when,
            _short_model(r["model"]),
            _fmt_score_compact(r["efficiency_score"]),
            f"{r['input_tokens']}+{r['output_tokens']}",
            _fmt_cost(r["cost_usd"]),
        )

    console.print()
    console.print("[bold red]Top Wasteful Prompts (last 30 days)[/bold red]")
    console.print(table)


def show_cost_by_model() -> None:
    rows = get_cost_by_model()
    if not rows:
        console.print("[dim]No usage data in the last 30 days.[/dim]")
        return

    table = Table(box=box.SIMPLE, show_header=True, padding=(0, 2))
    table.add_column("Model",         style="cyan", no_wrap=True)
    table.add_column("Requests",      justify="right")
    table.add_column("Input tokens",  justify="right")
    table.add_column("Output tokens", justify="right")
    table.add_column("Cost (USD)",    justify="right", style="bold")

    total_cost = 0.0
    total_requests = 0
    for r in rows:
        table.add_row(
            _short_model(r["model"]),
            str(r["requests"]),
            _fmt_tokens(r["input_tokens"]),
            _fmt_tokens(r["output_tokens"]),
            _fmt_cost(r["cost_usd"]),
        )
        total_cost += r["cost_usd"] or 0.0
        total_requests += r["requests"] or 0

    table.add_row("", "", "", "", "")
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]{total_requests}[/bold]",
        "",
        "",
        f"[bold]{_fmt_cost(total_cost)}[/bold]",
    )

    console.print()
    console.print("[bold blue]Cost by Model (last 30 days)[/bold blue]")
    console.print(table)
