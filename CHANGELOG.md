# Changelog

All notable changes to this project will be documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-05-11

### Fixed

- **CRITICAL** Model IDs with date suffix (e.g. `claude-haiku-4-5-20251001`) now correctly
  resolve to the right pricing — previously fell back to Sonnet rates (3.75× overcharge for Haiku)
- **CRITICAL** Cache savings in `tt report` now computed using per-model input vs cache_read rates
  instead of hardcoded Sonnet pricing
- **CRITICAL** Non-text message content (images, tool_use, tool_result blocks) no longer silently
  dropped — images become `[image]` placeholder, tool blocks become `[tool_use:name]`
- **HIGH** Streaming responses (`stream=True`) are now tracked — usage logged after stream ends
- **HIGH** `_ask_action()` no longer crashes with `EOFError` in CI/piped environments — defaults to send
- **HIGH** Efficiency scorer now penalises very large prompts properly:
  >500 tokens: −5, >1k: −10, >3k: −20, >10k: −35, >50k: −50
- **MEDIUM** `tt report --today` uses local time instead of UTC (fixes wrong-day display for non-UTC users)
- **MEDIUM** System messages excluded from rule analysis (were being flagged for FILLER_WORDS etc.)
- **MEDIUM** `tt run` now accepts `--interactive / -i`, `--session / -s`, `--threshold / -t` options
- **MEDIUM** `_replace_last_user_message()` emits a warning instead of silently failing when no user message found
- **MEDIUM** Missing model in `messages.create()` now emits an explicit warning instead of silently using Sonnet pricing
- **LOW** `check_filler_words()` and `check_text_speak()` no longer call `re.search()` twice per pattern
- **LOW** `tiktoken` import failure now emits a `warnings.warn` with install instructions instead of silent fallback
- **LOW** `optimize()` skipped entirely when there are no warnings (avoids unnecessary work)
- **LOW** DB schema now includes indexes on `timestamp`, `flagged`, `session_id`, `model` columns
- **LOW** DB connection errors now raise `RuntimeError` with a human-readable message
- **LOW** `PromptAnalysis.token_savings` renamed to `token_delta` (was misleadingly named; field is positive for savings, negative when constraints are added)
- **LOW** CLI `analyze` command renamed internally to `analyze_prompt` to prevent function name shadowing the preflight import
- **LOW** SPEC.md updated: rule count corrected from 8 to 11 (TEXT_SPEAK, VAGUE_CLOSING, TOPIC_DRIFT)

## [0.2.0] - 2026-05-11

### Added

- `tt run script.py` — zero code change tracking; wraps any existing Python script
- `token_tracker.patch()` — one-line monkey-patch for `anthropic.Anthropic`
- `TEXT_SPEAK` rule (low): catches informal shorthand like "can u", "ur", "plz"
- `VAGUE_CLOSING` rule (high): catches prompts ending with no specific ask ("can u tell me", "any thoughts?")
- `TOPIC_DRIFT` rule (medium): catches mid-prompt topic switches

### Improved

- `VAGUE_INTENT` — now catches "can u tell me", "i want to know", "do you know anything about"
- `AMBIGUOUS_PRONOUN` — now catches 3+ "it" references in any length prompt
- `MISSING_SCOPE` — now catches "i don't know about X" as open-ended explanation

## [0.1.0] - 2026-05-10

Initial release.

### Added

- `TrackedClient` — drop-in wrapper around `anthropic.Anthropic`
- SQLite logging at `~/.token_tracker/usage.db` (sessions + usage records)
- Pre-flight analyzer with 8 rules:
  `VAGUE_INTENT`, `OPEN_ENDED_TASK`, `WALL_OF_TEXT`, `MISSING_FORMAT`,
  `MISSING_SCOPE`, `REDUNDANT_CONTEXT`, `FILLER_WORDS`, `AMBIGUOUS_PRONOUN`
- 0–100 efficiency scoring with severity-based penalties
- Rule-based prompt optimizer with side-by-side rewrite diff
- Interactive `[s]end / [o]ptimize+send / [c]ancel` flow
- CLI: `tt report`, `tt sessions`, `tt analyze`, `tt top-waste`, `tt cost-model`, `tt demo`
- Cost calculation for `claude-opus-4-7`, `claude-sonnet-4-6`, `claude-haiku-4-5`
