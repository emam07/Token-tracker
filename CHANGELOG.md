# Changelog

All notable changes to this project will be documented in this file. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
