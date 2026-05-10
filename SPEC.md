# Token Tracker — Project Specification

**Version**: 1.0  
**Date**: 2026-05-10  
**Analogy**: Gas optimization in Solidity — but for LLM prompts.

---

## 1. Problem Statement

LLM API costs are invisible until the bill arrives. Developers send vague, bloated, or redundant prompts with no feedback loop. There is no tool that acts *before* a prompt is sent — warning the developer, scoring efficiency, and suggesting a leaner rewrite.

This project builds that tool.

---

## 2. What We Are Building

A Python SDK + CLI that wraps the Anthropic client and adds three capabilities:

| Layer | What it does | Analogy |
|---|---|---|
| **Token Tracker** | Records every API call — tokens in, tokens out, cost, session | Gas meter |
| **Pre-flight Analyzer** | Scores a prompt *before sending* — flags waste, vagueness, missing constraints | Gas estimator / Solidity linter |
| **Prompt Optimizer** | Suggests a rewritten prompt that achieves the same intent with fewer tokens | Compiler optimizer |

---

## 3. Non-Goals (what we are NOT building)

- No web UI in v1 — CLI only
- No multi-provider support in v1 — Claude/Anthropic only
- No real-time keystroke analysis — analyze on explicit call, not on every keypress
- No model fine-tuning
- No prompt compression via neural models (LLMLingua-style) in v1 — rule-based only

---

## 4. Tech Stack

| Concern | Tool | Why |
|---|---|---|
| Language | Python 3.11+ | Anthropic SDK is Python-first |
| LLM SDK | `anthropic` | Target platform |
| Token estimation | `tiktoken` | Fast, offline, no API call needed |
| Storage | SQLite via `sqlite3` (stdlib) | Zero dependencies, portable |
| Terminal UI | `rich` | Tables, progress bars, color |
| CLI | `typer` | Clean argument parsing |
| Text analysis | `regex` + simple heuristics | No heavy NLP deps in v1 |
| Packaging | `pyproject.toml` | Modern Python packaging |

---

## 5. Architecture

```
token_tracker/
├── core/
│   ├── client.py          # TrackedClient — wraps anthropic.Anthropic
│   ├── tracker.py         # TokenTracker — logs usage to SQLite
│   └── models.py          # Pydantic/dataclass models for UsageRecord, Session
├── analyzer/
│   ├── preflight.py       # PromptAnalyzer — scores prompt before send
│   ├── rules.py           # Rule definitions (vagueness, redundancy, constraints)
│   └── scorer.py          # Computes EfficiencyScore (0–100)
├── optimizer/
│   └── rewriter.py        # PromptOptimizer — suggests rewritten prompt
├── storage/
│   └── db.py              # SQLite schema, queries, migrations
├── cli/
│   └── main.py            # typer app — `tt` command
├── dashboard/
│   └── report.py          # Rich tables for usage reports
└── __init__.py
```

---

## 6. Data Models

### UsageRecord
```python
@dataclass
class UsageRecord:
    id: str                    # uuid
    session_id: str
    timestamp: datetime
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    cost_usd: float            # calculated at write time
    prompt_hash: str           # sha256 of prompt (not full text, for privacy)
    efficiency_score: int      # 0-100, null if analyzer skipped
    flagged: bool              # true if pre-flight raised warnings
```

### PromptAnalysis
```python
@dataclass
class PromptAnalysis:
    estimated_input_tokens: int
    estimated_cost_usd: float
    efficiency_score: int      # 0-100
    warnings: list[Warning]    # list of flagged issues
    suggested_rewrite: str     # optimized prompt text
    token_savings: int         # estimated tokens saved by rewrite
```

### Warning
```python
@dataclass
class Warning:
    rule: str          # e.g. "VAGUE_INTENT"
    severity: str      # "low" | "medium" | "high"
    message: str       # human-readable explanation
    suggestion: str    # specific fix
```

---

## 7. Component Specs

### 7.1 TrackedClient (`core/client.py`)

Drop-in replacement for `anthropic.Anthropic`. Intercepts `messages.create()`.

```python
# Usage — identical to normal Anthropic SDK
client = TrackedClient(api_key="...", session_name="my-app")
response = client.messages.create(model="claude-sonnet-4-6", ...)
```

**Behavior:**
1. Before sending: run `PromptAnalyzer` if `analyze=True` (default)
2. If warnings exist and `interactive=True`: print warnings + ask user to proceed/edit
3. Send the request
4. On response: extract `usage` block, write `UsageRecord` to SQLite
5. Return unmodified response (transparent wrapper)

**Config flags:**
- `analyze: bool = True` — run pre-flight
- `interactive: bool = True` — prompt user on warnings
- `auto_optimize: bool = False` — silently use rewritten prompt if score < threshold
- `warn_threshold: int = 60` — score below this triggers warning

---

### 7.2 PromptAnalyzer (`analyzer/preflight.py`)

Runs **before** the API call. Zero network calls. Fast.

**Input**: prompt text + model name  
**Output**: `PromptAnalysis`

**Steps:**
1. Estimate token count via `tiktoken`
2. Run all rules (see 7.3)
3. Compute efficiency score
4. Generate rewrite suggestion (rule-based, no API call)

---

### 7.3 Rules (`analyzer/rules.py`)

Each rule is a function: `(prompt: str) -> Warning | None`

| Rule ID | Detects | Severity | Example trigger |
|---|---|---|---|
| `VAGUE_INTENT` | No clear task verb | high | "tell me something about X" |
| `MISSING_FORMAT` | No output format specified | medium | asking for a list but not saying "as bullet points" |
| `MISSING_SCOPE` | No length/depth constraint | medium | "explain X" with no word limit |
| `FILLER_WORDS` | Fluff that adds tokens, zero meaning | low | "please", "could you kindly", "I was wondering if" |
| `REDUNDANT_CONTEXT` | Same info repeated in prompt | medium | restating the system prompt in user message |
| `WALL_OF_TEXT` | Unstructured dump > 500 tokens | high | pasting 2000 words without summarizing |
| `AMBIGUOUS_PRONOUN` | "it", "this", "that" without clear referent | low | "fix it" — fix what? |
| `OPEN_ENDED_TASK` | Task has unbounded output | high | "write everything about X" |

---

### 7.4 Efficiency Score (`analyzer/scorer.py`)

Score = 100 - penalty_sum

| Condition | Penalty |
|---|---|
| Each HIGH warning | -20 |
| Each MEDIUM warning | -10 |
| Each LOW warning | -5 |
| Estimated tokens > 1000 | -10 |
| Estimated tokens > 3000 | -20 |

Score clamped to [0, 100].

**Labels:**
- 80–100: Efficient
- 60–79: Acceptable
- 40–59: Wasteful — warning shown
- 0–39: Very wasteful — hard block (if `interactive=True`)

---

### 7.5 PromptOptimizer (`optimizer/rewriter.py`)

Rule-based rewriter. No API call. Fast.

**Transformations:**
1. Strip filler words (regex substitution list)
2. Add format constraint if missing: append `"Respond in bullet points."` or `"Keep response under 200 words."`
3. Trim redundant repetition (simple cosine similarity on sentences, flag top duplicate)
4. Flag wall-of-text: suggest `"Summarize the following before using as context:"`

Output: rewritten prompt string + token delta.

---

### 7.6 Storage (`storage/db.py`)

SQLite, single file: `~/.token_tracker/usage.db`

**Schema:**
```sql
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    name TEXT,
    started_at TEXT,
    ended_at TEXT
);

CREATE TABLE usage_records (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    timestamp TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cache_read_tokens INTEGER,
    cache_write_tokens INTEGER,
    cost_usd REAL,
    prompt_hash TEXT,
    efficiency_score INTEGER,
    flagged INTEGER
);
```

---

### 7.7 CLI (`cli/main.py`)

Command: `tt`

```
tt report                  # show today's usage summary
tt report --week           # last 7 days
tt report --month          # last 30 days
tt sessions                # list all sessions
tt analyze "your prompt"   # run pre-flight analyzer on a prompt, no API call
tt top-waste               # show 10 most wasteful prompts this month
tt cost-model              # show cost breakdown by model
```

---

### 7.8 Dashboard output (sample)

```
Token Usage — Today (2026-05-10)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Input tokens      :  12,450
  Output tokens     :   4,230
  Cache read        :   8,100  (saved $0.041)
  Total cost        :  $0.087
  Requests          :     24
  Avg efficiency    :     71 / 100
  Flagged prompts   :      5

Top warnings today:
  MISSING_FORMAT     x8
  VAGUE_INTENT       x4
  WALL_OF_TEXT       x2
```

---

## 8. Development Phases

### Phase 1 — Foundation (Week 1)
- [ ] Project scaffolding (`pyproject.toml`, folder structure)
- [ ] SQLite schema + `db.py`
- [ ] `UsageRecord` dataclass
- [ ] `TrackedClient` basic wrapper (no analyzer yet)
- [ ] Post-call token logging
- [ ] `tt report` CLI command

**Done when**: wrap a real Claude call, see it logged, run `tt report` and see output.

---

### Phase 2 — Pre-flight Analyzer (Week 2)
- [ ] `tiktoken` integration for token estimation
- [ ] All 8 rules implemented in `rules.py`
- [ ] `EfficiencyScore` computation
- [ ] `PromptAnalysis` dataclass
- [ ] Warning output in terminal (Rich formatting)
- [ ] `tt analyze "prompt"` CLI command

**Done when**: run `tt analyze "tell me something about Python"` and see score + warnings.

---

### Phase 3 — Prompt Optimizer (Week 2–3)
- [ ] Filler word strip list
- [ ] Format constraint injector
- [ ] Redundancy detector
- [ ] Wall-of-text handler
- [ ] Side-by-side diff output (original vs optimized, token delta)

**Done when**: optimizer takes a bad prompt and outputs a leaner version with token count shown.

---

### Phase 4 — Interactive Mode + Full Dashboard (Week 3)
- [ ] Interactive warning flow in `TrackedClient`
- [ ] `tt top-waste` command
- [ ] `tt sessions` command
- [ ] `tt cost-model` command
- [ ] Session naming support

**Done when**: full end-to-end flow — write prompt → see warning → edit or proceed → call logged → view in dashboard.

---

### Phase 5 — Packaging (Week 4)
- [ ] `pyproject.toml` with entry point for `tt`
- [ ] `pip install token-tracker` works
- [ ] README with quickstart
- [ ] Example scripts

**Done when**: fresh machine, `pip install token-tracker`, wrap one Claude call, see it tracked.

---

### Phase 6 — Open Source Release (Week 4–5)

Goal: make the project contributor-friendly and discoverable. Every item here serves either **adoption** (more users) or **contribution** (more PRs = better GitHub profile signal).

#### 6.1 Repository hygiene
- [ ] Clean folder structure matches spec exactly — no leftover scratch files
- [ ] `LICENSE` — MIT (maximizes adoption, no friction for commercial users)
- [ ] `.gitignore` — exclude `usage.db`, `.env`, `__pycache__`, `.venv`
- [ ] `pyproject.toml` — version `0.1.0`, author, description, keywords (`llm`, `token`, `anthropic`, `prompt-optimization`)

#### 6.2 README (the most important file for GitHub stars)
- [ ] Hero section: one-line description + the gas optimization analogy
- [ ] Demo GIF — record terminal session: bad prompt → warnings → optimized rewrite → `tt report`
- [ ] Quickstart: 3 commands to install and see output
- [ ] Feature list with screenshots of dashboard output
- [ ] Badge row: PyPI version, Python version, license, CI status

#### 6.3 PyPI publish
- [ ] `pip install token-tracker` works from PyPI (not just local install)
- [ ] GitHub Action: auto-publish to PyPI on version tag (`v*`)
- [ ] Version bumping convention documented (`0.1.x` = patches, `0.x.0` = new features)

#### 6.4 CI — GitHub Actions
- [ ] `ci.yml`: run `pytest` on push + PR (Python 3.11, 3.12)
- [ ] Lint: `ruff` check on every PR
- [ ] Badge in README shows passing

#### 6.5 Contributor infrastructure
- [ ] `CONTRIBUTING.md` — how to add a new rule in `rules.py` (this is the lowest-friction first contribution — ~10 lines of Python)
- [ ] Issue templates:
  - "Suggest a new rule" — fields: what pattern it catches, example prompt, severity
  - "Bug report"
  - "Feature request"
- [ ] PR template — checklist: rule has a test, rule ID added to docs
- [ ] `CHANGELOG.md` — start at `0.1.0`

#### 6.6 Test coverage (required before open source — public bugs hurt credibility)
- [ ] Unit tests for all 8 rules in `rules.py`
- [ ] Unit test for scorer — known input → expected score
- [ ] Unit test for rewriter — known bad prompt → expected transformation
- [ ] Integration test for `TrackedClient` using Anthropic SDK mock

#### 6.7 Community seeding (do after code is solid)
- [ ] Post on Reddit: r/LocalLLaMA, r/MachineLearning, r/Python
- [ ] Post on Hacker News: "Show HN: Token Tracker — a gas estimator for LLM prompts"
- [ ] Share on X/Twitter with demo GIF
- [ ] Add to `awesome-llm-tools` lists on GitHub

**Done when**: repo is public, `pip install token-tracker` works, CI is green, CONTRIBUTING.md explains how to add a rule, demo GIF is in README.

---

## 9. Token Cost Reference (at spec time)

| Model | Input (per 1M) | Output (per 1M) | Cache read (per 1M) |
|---|---|---|---|
| claude-opus-4-7 | $15.00 | $75.00 | $1.50 |
| claude-sonnet-4-6 | $3.00 | $15.00 | $0.30 |
| claude-haiku-4-5 | $0.80 | $4.00 | $0.08 |

Cost calculation in `tracker.py` uses these constants. Update when Anthropic changes pricing.

---

## 10. Does Building This Tool Save Tokens?

Yes — directly.

| Without this tool | With this tool |
|---|---|
| Vague prompt sent → Claude asks clarifying questions → 2–3 extra round trips | Pre-flight catches vagueness → you fix it → one round trip |
| No format specified → Claude writes 800 words when you needed 100 | MISSING_FORMAT rule flags it → you add constraint → 6× fewer output tokens |
| Redundant context pasted every message | REDUNDANT_CONTEXT rule flags it → you use cache or trim → cache saves 90% of input cost |
| No visibility into costs → no behavior change | Daily report shows cost per session → developer adjusts habits |

Conservative estimate: **30–50% reduction in token spend** for a developer who acts on warnings.

---

## 11. What Each Dev Session Needs to Know

Before starting any phase, the developer (human or AI) reads:
- This spec (section 7.x for the component being built)
- The data models (section 6)
- The phase checklist (section 8)

No other context needed. Each component has defined inputs, outputs, and behavior. This document IS the context — no re-explaining required.
