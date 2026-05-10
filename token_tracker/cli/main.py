import typer

from token_tracker.dashboard.report import show_analysis, show_report, show_sessions

app = typer.Typer(
    name="tt",
    help="Token Tracker — gas optimizer for LLM prompts",
    add_completion=False,
)


@app.command()
def report(
    week:  bool = typer.Option(False, "--week",  help="Show last 7 days"),
    month: bool = typer.Option(False, "--month", help="Show last 30 days"),
) -> None:
    """Show token usage summary."""
    if month:
        show_report("month")
    elif week:
        show_report("week")
    else:
        show_report("today")


@app.command()
def sessions(
    limit: int = typer.Option(20, "--limit", "-n", help="Max sessions to show"),
) -> None:
    """List recent sessions."""
    show_sessions(limit)


@app.command()
def analyze(
    prompt: str = typer.Argument(..., help="Prompt text to analyze"),
    model:  str = typer.Option("claude-sonnet-4-6", "--model", "-m", help="Target model"),
) -> None:
    """Analyze a prompt before sending — no API call made."""
    from token_tracker.analyzer.preflight import analyze as run_analysis
    result = run_analysis(prompt, model)
    show_analysis(result, original_prompt=prompt)


@app.command(name="top-waste")
def top_waste(
    limit: int = typer.Option(10, "--limit", "-n", help="Max rows to show"),
) -> None:
    """Show the most wasteful prompts (flagged, ranked by cost)."""
    from token_tracker.dashboard.report import show_top_waste
    show_top_waste(limit)


@app.command(name="cost-model")
def cost_model() -> None:
    """Show cost breakdown by model (last 30 days)."""
    from token_tracker.dashboard.report import show_cost_by_model
    show_cost_by_model()


@app.command()
def demo() -> None:
    """Guided walkthrough of every feature. Zero API calls — safe to run anytime."""
    from token_tracker.cli.demo import run_demo
    run_demo()


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def run(ctx: typer.Context) -> None:
    """Run any Python script with automatic token tracking — no code changes needed.

    Examples:
        tt run script.py
        tt run script.py arg1 arg2
        tt run python script.py
    """
    import runpy
    import sys

    from token_tracker.autopatch import patch

    args = ctx.args
    if not args:
        raise typer.BadParameter("Provide a script path, e.g.: tt run script.py")

    script = args[0]
    script_args = args[1:]

    if script in ("python", "python3", "python.exe", "python3.exe"):
        if not script_args:
            raise typer.BadParameter("Provide a script path after 'python'.")
        script = script_args[0]
        script_args = script_args[1:]

    patch(interactive=False)
    sys.argv = [script] + list(script_args)

    try:
        runpy.run_path(script, run_name="__main__")
    except SystemExit as exc:
        raise SystemExit(exc.code) from None


if __name__ == "__main__":
    app()
