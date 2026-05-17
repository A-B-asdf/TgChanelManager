import hashlib
import os
import sqlite3
from typing import Dict, List, Optional, Set

from content_scheduler.core.config import Config
from content_scheduler.core.schemas import ScheduleSettings


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def init_db():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                cron TEXT NOT NULL,
                timezone TEXT NOT NULL,
                active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS published_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_published_content_account_hash
            ON published_content(account_id, content_hash)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scheduled_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                schedule_id INTEGER,
                slot_key TEXT NOT NULL,
                source TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(account_id, slot_key)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_scheduled_runs_account_slot
            ON scheduled_runs(account_id, slot_key)
            """
        )


def save_schedule_to_db(account_id: int, settings: ScheduleSettings) -> int:
    with sqlite3.connect(Config.DB_PATH) as conn:
        if settings.active:
            conn.execute(
                "UPDATE schedules SET active = 0 WHERE account_id = ? AND active = 1",
                (account_id,),
            )
        cur = conn.execute(
            "INSERT INTO schedules (account_id, cron, timezone, active) VALUES (?, ?, ?, ?)",
            (account_id, settings.cron, settings.timezone, settings.active),
        )
        return int(cur.lastrowid)


def ensure_active_schedule(account_id: int, cron: str, timezone: str) -> int:
    """Return an active schedule id for account_id, creating one if none exists."""
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM schedules WHERE account_id = ? AND active = 1 ORDER BY id DESC LIMIT 1",
            (account_id,),
        ).fetchone()
        if row:
            return int(row["id"])
        cur = conn.execute(
            "INSERT INTO schedules (account_id, cron, timezone, active) VALUES (?, ?, ?, 1)",
            (account_id, cron, timezone),
        )
        return int(cur.lastrowid)


def get_schedule_by_id(schedule_id: int) -> Optional[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,)).fetchone()
        return dict(row) if row else None


def get_schedules_by_account(account_id: int) -> List[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM schedules WHERE account_id = ? ORDER BY id DESC",
            (account_id,),
        ).fetchall()
        return [dict(row) for row in rows]


def get_active_schedules() -> List[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM schedules WHERE active = 1 ORDER BY id ASC").fetchall()
        return [dict(row) for row in rows]


def delete_schedule(schedule_id: int) -> bool:
    with sqlite3.connect(Config.DB_PATH) as conn:
        cur = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        return cur.rowcount > 0


def content_hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def get_recent_content_hashes(account_id: int, limit: int = 100) -> Set[str]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        rows = conn.execute(
            """
            SELECT content_hash FROM published_content
            WHERE account_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (account_id, limit),
        ).fetchall()
        return {row[0] for row in rows}


def save_published_content(account_id: int, text: str) -> None:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute(
            "INSERT INTO published_content (account_id, content_hash, text) VALUES (?, ?, ?)",
            (account_id, content_hash(text), text),
        )


def mark_scheduled_run(account_id: int, schedule_id: int, slot_key: str, source: str) -> bool:
    """Insert a scheduled run lock. Returns False if this account/hour already ran."""
    try:
        with sqlite3.connect(Config.DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO scheduled_runs (account_id, schedule_id, slot_key, source)
                VALUES (?, ?, ?, ?)
                """,
                (account_id, schedule_id, slot_key, source),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def get_recent_scheduled_runs(account_id: Optional[int] = None, limit: int = 20) -> List[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if account_id is None:
            rows = conn.execute(
                "SELECT * FROM scheduled_runs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM scheduled_runs WHERE account_id = ? ORDER BY id DESC LIMIT ?",
                (account_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]


init_db()
