import os
import sqlite3
from typing import Dict, List, Optional

from content_scheduler.core.config import Config
from content_scheduler.core.schemas import ScheduleSettings


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


def save_schedule_to_db(account_id: int, settings: ScheduleSettings) -> int:
    with sqlite3.connect(Config.DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO schedules (account_id, cron, timezone, active) VALUES (?, ?, ?, ?)",
            (account_id, settings.cron, settings.timezone, settings.active),
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
        rows = conn.execute("SELECT * FROM schedules WHERE active = 1").fetchall()
        return [dict(row) for row in rows]


def delete_schedule(schedule_id: int) -> bool:
    with sqlite3.connect(Config.DB_PATH) as conn:
        cur = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        return cur.rowcount > 0


init_db()
