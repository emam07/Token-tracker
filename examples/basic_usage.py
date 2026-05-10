"""
Basic Token Tracker usage — drop-in replacement for anthropic.Anthropic.

Every call goes through:
  1. Pre-flight analysis (warns on vague/wasteful prompts)
  2. The Anthropic API
  3. SQLite logging (input/output tokens, cost, efficiency score)

Run:
    pip install promptmeter
    export ANTHROPIC_API_KEY="sk-ant-..."
    python examples/basic_usage.py

Then view your usage:
    tt report
    tt cost-model
    tt top-waste
"""
import os

from token_tracker import TrackedClient


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY first.")

    client = TrackedClient(
        api_key=api_key,
        session_name="basic-usage-example",
        analyze=True,            # default: run pre-flight before each call
        interactive=False,       # set True to be prompted on bad prompts
        warn_threshold=70,       # show warnings for any score below 70
    )

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=128,
        messages=[
            {
                "role": "user",
                "content": "List the 3 most popular Python web frameworks as a numbered list.",
            }
        ],
    )

    print("Claude:", response.content[0].text)


if __name__ == "__main__":
    main()
