# Contributing to Token Tracker

Thanks for considering a contribution. The lowest-friction way to help is **adding a new rule to the pre-flight analyzer** — see below.

---

## Setting up

```bash
git clone https://github.com/emam07/token-tracker.git
cd token-tracker
python -m venv .venv
.venv/Scripts/activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -e ".[dev]"
```

Run the test suite:
```bash
pytest
ruff check .
```

---

## Adding a new rule (great first PR)

A "rule" detects one wasteful prompt pattern. Adding one takes ~10 lines.

**1.** Open `token_tracker/analyzer/rules.py`.

**2.** Write your rule as a function returning `Warning | None`:

```python
def check_my_pattern(prompt: str) -> Warning | None:
    if re.search(r"\bsome bad pattern\b", prompt, re.IGNORECASE):
        return Warning(
            rule="MY_RULE_ID",
            severity="medium",          # "low" | "medium" | "high"
            message="Short explanation of what's wrong.",
            suggestion="Concrete advice on how to fix it.",
        )
    return None
```

**3.** Add the function to the `RULES` list at the bottom of the file.

**4.** Add a unit test in `tests/test_rules.py`:

```python
def test_my_rule_triggers_on_bad_prompt():
    result = check_my_pattern("contains some bad pattern here")
    assert result is not None
    assert result.rule == "MY_RULE_ID"

def test_my_rule_skips_clean_prompt():
    assert check_my_pattern("a perfectly fine prompt") is None
```

**5.** Add the rule to the table in `README.md`.

That's it. Open the PR.

---

## Reporting a false positive

Open an issue with the **"Bug"** template and include:
- The exact prompt that triggered the warning
- Which rule fired
- Why you think it's wrong

---

## Pull request checklist

- [ ] New rule has a unit test (positive + negative case)
- [ ] `pytest` passes locally
- [ ] `ruff check .` passes locally
- [ ] README rule table updated (if a new rule was added)
- [ ] CHANGELOG entry added under `## [Unreleased]`

---

## Code style

- 100-char lines max
- Type hints on public functions
- No comments explaining *what* the code does — only *why*, when non-obvious
- Prefer stdlib over new dependencies

---

## Questions

Open a [discussion](https://github.com/emam07/token-tracker/discussions) before a big change.
