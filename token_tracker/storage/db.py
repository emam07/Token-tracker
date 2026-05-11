import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from token_tracker.core.models import Session, UsageRecord

DB_PATH = Path.home() / ".token_tracker" / "usage.db"


def get_connection() -> sqlite3.Connection:
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        _ensure_schema(conn)
        return conn
    except sqlite3.Error as exc:
        raise RuntimeError(
            f"Token Tracker: cannot open database at {DB_PATH}. "
            f"Check disk space and file permissions.\nOriginal error: {exc}"
        ) from exc


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id          TEXT PRIMARY KEY,
            name        TEXT,
            started_at  TEXT,
            ended_at    TEXT
        );

        CREATE TABLE IF NOT EXISTS usage_records (
            id                  TEXT PRIMARY KEY,
            session_id          TEXT,
            timestamp           TEXT,
            model               TEXT,
            input_tokens        INTEGER,
            output_tokens       INTEGER,
            cache_read_tokens   INTEGER,
            cache_write_tokens  INTEGER,
            cost_usd            REAL,
            prompt_hash         TEXT,
            efficiency_score    INTEGER,
            flagged             INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_records(timestamp);
        CREATE INDEX IF NOT EXISTS idx_usage_flagged   ON usage_records(flagged);
        CREATE INDEX IF NOT EXISTS idx_usage_session   ON usage_records(session_id);
        CREATE INDEX IF NOT EXISTS idx_usage_model     ON usage_records(model);
    """)


def init_db() -> None:
    # Just open a connection — get_connection() runs _ensure_schema for us.
    get_connection().close()


def insert_session(session: Session) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, name, started_at, ended_at) VALUES (?, ?, ?, ?)",
            (
                session.id,
                session.name,
                session.started_at.isoformat(),
                session.ended_at.isoformat() if session.ended_at else None,
            ),
        )


def insert_usage_record(record: UsageRecord) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO usage_records
                (id, session_id, timestamp, model, input_tokens, output_tokens,
                 cache_read_tokens, cache_write_tokens, cost_usd, prompt_hash,
                 efficiency_score, flagged)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.session_id,
                record.timestamp.isoformat(),
                record.model,
                record.input_tokens,
                record.output_tokens,
                record.cache_read_tokens,
                record.cache_write_tokens,
                record.cost_usd,
                record.prompt_hash,
                record.efficiency_score,
                int(record.flagged),
            ),
        )


def _summary_query(where_clause: str, params: tuple):
    with get_connection() as conn:
        return conn.execute(
            f"""
            SELECT
                COUNT(*)                                                        AS requests,
                COALESCE(SUM(input_tokens), 0)                                  AS input_tokens,
                COALESCE(SUM(output_tokens), 0)                                 AS output_tokens,
                COALESCE(SUM(cache_read_tokens), 0)                             AS cache_read_tokens,
                COALESCE(SUM(cache_write_tokens), 0)                            AS cache_write_tokens,
                COALESCE(SUM(cost_usd), 0)                                      AS cost_usd,
                COALESCE(SUM(flagged), 0)                                       AS flagged_count,
                AVG(CASE WHEN efficiency_score IS NOT NULL
                         THEN efficiency_score END)                             AS avg_efficiency
            FROM usage_records
            {where_clause}
            """,
            params,
        ).fetchone()


def get_usage_today():
    today = datetime.now().date().isoformat()  # local time — matches stored timestamps
    return _summary_query("WHERE timestamp LIKE ?", (f"{today}%",))


def get_usage_range(days: int):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    return _summary_query("WHERE timestamp >= ?", (since,))


def get_sessions(limit: int = 20):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM sessions ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()


def get_top_waste(limit: int = 10, days: int = 30):
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT prompt_hash, model, cost_usd, efficiency_score,
                   input_tokens, output_tokens, timestamp
            FROM usage_records
            WHERE flagged = 1 AND timestamp >= ?
            ORDER BY cost_usd DESC
            LIMIT ?
            """,
            (since, limit),
        ).fetchall()


def get_cost_by_model(days: int = 30):
    since = (datetime.now() - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT model,
                   COUNT(*)                              AS requests,
                   COALESCE(SUM(input_tokens),  0)       AS input_tokens,
                   COALESCE(SUM(output_tokens), 0)       AS output_tokens,
                   COALESCE(SUM(cost_usd),      0)       AS cost_usd
            FROM usage_records
            WHERE timestamp >= ?
            GROUP BY model
            ORDER BY cost_usd DESC
            """,
            (since,),
        ).fetchall()


def get_cache_savings(period: str):
    """Return (model, cache_read_tokens) rows for the period so callers can compute per-model savings."""
    if period == "today":
        today = datetime.now().date().isoformat()
        clause, params = "WHERE timestamp LIKE ?", (f"{today}%",)
    elif period == "week":
        since = (datetime.now() - timedelta(days=7)).isoformat()
        clause, params = "WHERE timestamp >= ?", (since,)
    else:
        since = (datetime.now() - timedelta(days=30)).isoformat()
        clause, params = "WHERE timestamp >= ?", (since,)

    with get_connection() as conn:
        return conn.execute(
            f"""
            SELECT model, COALESCE(SUM(cache_read_tokens), 0) AS cache_read_tokens
            FROM usage_records {clause}
            GROUP BY model
            """,
            params,
        ).fetchall()
