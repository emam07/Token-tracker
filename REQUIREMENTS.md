# Token Tracker — Requirements

---

## 1. Database

**What**: SQLite  
**Where**: Single file at `~/.token_tracker/usage.db` on the host machine  
**Why SQLite and not Postgres/MySQL:**

- This tool runs as a local developer utility — one user, one machine, low write volume
- SQLite is stdlib Python (`import sqlite3`) — zero extra install, zero server process
- A developer making 100 API calls/day generates ~100 rows/day — SQLite handles millions of rows fine at this scale
- The DB file is portable — copy it, back it up, inspect it with any SQLite viewer
- No concurrent writes from multiple processes (single CLI process at a time)

**When to reconsider**: Only if you add a web dashboard with multiple simultaneous users writing to the DB, or if you want to sync usage across multiple machines. Neither is in scope for v1.

**Storage estimate**:  
Each `usage_record` row ≈ 200 bytes.  
100 calls/day × 365 days = 36,500 rows ≈ **~7 MB/year**. Negligible.

---

## 2. External APIs

### 2.1 Anthropic API (required)
**Why**: The tool wraps the Anthropic SDK — it needs a real API key to make Claude calls on behalf of the developer.  
**Key**: Set via `ANTHROPIC_API_KEY` environment variable. Never stored in the DB.  
**Calls made by the tool itself**: None in v1. The tool intercepts the developer's own API calls — it does not make additional Claude calls for analysis. Analysis is rule-based and offline.

> Note: Phase 3 optionally adds a "meta-rewrite" feature where Haiku is called to rewrite a bad prompt. This is opt-in (`--use-ai-rewrite` flag) and clearly marked as making an extra API call. Off by default.

### 2.2 No other external APIs
- Token estimation uses `tiktoken` — runs fully offline, no network call
- Rules engine is pure Python — no network call
- Dashboard reads from local SQLite — no network call

---

## 3. Python Package Dependencies

```
anthropic          # Anthropic SDK — wraps this for tracking
tiktoken           # Offline token estimation before send
rich               # Terminal tables, colors, progress bars
typer              # CLI argument parsing
```

No other third-party dependencies. Everything else uses Python stdlib.

Install size estimate: ~50 MB (tiktoken includes BPE vocab files)

---

## 4. Minimum Server / Hosting Requirements

This is a **local developer tool** — it runs on the developer's own machine, not a server. There is no web server, no daemon, no always-on process.

However, if you want to host this as a **shared team service** (e.g., a central dashboard that aggregates token usage across a team), here are the minimums:

### 4.1 Local machine (primary use case — v1)

| Resource | Minimum | Notes |
|---|---|---|
| OS | Windows 10 / macOS 12 / Ubuntu 20.04 | Any modern OS |
| Python | 3.11+ | f-strings, dataclasses, match statements |
| RAM | 512 MB free | tiktoken vocab loads ~30 MB into memory |
| Disk | 200 MB | 50 MB deps + DB growth over time |
| Network | Only what Claude API needs | Tool itself makes no extra calls |
| CPU | Any modern CPU | Analysis runs in < 50ms |

### 4.2 Shared team server (future — if you build a web dashboard)

| Resource | Minimum | Notes |
|---|---|---|
| OS | Ubuntu 22.04 LTS | Stable, well-supported |
| CPU | 1 vCPU | Low compute — mostly I/O |
| RAM | 1 GB | Python process + SQLite in memory |
| Disk | 10 GB SSD | DB + logs + room to grow |
| Network | 1 Mbps | Serving a small team dashboard |
| Python | 3.11+ | Same as above |

**Cheapest cloud option that meets this**: AWS t3.micro ($8/mo), DigitalOcean Basic Droplet ($6/mo), Hetzner CX11 (~€4/mo). Any of these is overkill for a small team — the tool is not compute-heavy.

### 4.3 What you do NOT need

- No Docker required (though it works fine in Docker)
- No Kubernetes, no load balancer, no message queue
- No Redis, no Postgres, no external DB
- No GPU
- No reverse proxy unless you add a web UI later

---

## 5. Summary

| Dependency | Required | Why |
|---|---|---|
| Python 3.11+ | Yes | Runtime |
| SQLite | Yes (bundled) | Local usage storage |
| Anthropic API key | Yes | Developer's own key for their Claude calls |
| `tiktoken` | Yes | Offline token estimation |
| `rich` + `typer` | Yes | Terminal UI + CLI |
| Any server | No (v1) | Runs locally on dev machine |
| Internet (beyond Claude API) | No | All analysis is offline |
