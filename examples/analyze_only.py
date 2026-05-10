"""
Standalone pre-flight analyzer — no API key needed, no API call made.

Use this to score a prompt offline before deciding whether to send it.

Run:
    python examples/analyze_only.py
"""
from token_tracker.analyzer.preflight import analyze

PROMPTS = [
    "Please could you kindly tell me something about Python and explain everything",
    "I was wondering if you could please write the function and add docstrings",
    "List the top 5 Python web frameworks as a numbered list, one line each",
]


def main() -> None:
    for prompt in PROMPTS:
        result = analyze(prompt, model="claude-sonnet-4-6")
        print("-" * 60)
        print(f"PROMPT: {prompt!r}")
        print(f"  Estimated tokens : {result.estimated_input_tokens}")
        print(f"  Efficiency score : {result.efficiency_score} / 100")
        print(f"  Warnings         : {len(result.warnings)}")
        for w in result.warnings:
            print(f"    [{w.severity.upper():6}] {w.rule}: {w.message}")
        if result.suggested_rewrite:
            print(f"  Rewrite          : {result.suggested_rewrite}")
            print(f"  Token delta      : {-result.token_savings:+d} (vs original)")


if __name__ == "__main__":
    main()
