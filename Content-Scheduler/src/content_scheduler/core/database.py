import os
import sqlite3
from typing import Dict, List
from content_scheduler.core.config import Config
from content_scheduler.core.schemas import ScheduleSettings

def init_db():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                cron TEXT NOT NULL,
                timezone TEXT NOT NULL,
                active BOOLEAN NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_schedule_to_db(account_id: int, settings: ScheduleSettings) -> int:
    with sqlite3.connect(Config.DB_PATH) as conn:
        cursor = conn.execute(
            "INSERT INTO schedules (account_id, cron, timezone, active) VALUES (?, ?, ?, ?)",
            (account_id, settings.cron, settings.timezone, settings.active)
        )
        return cursor.lastrowid

def get_schedules_by_account(account_id: int) -> List[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM schedules WHERE account_id = ?", (account_id,)).fetchall()
        return [dict(row) for row in rows]

def delete_schedule(schedule_id: int) -> bool:
    with sqlite3.connect(Config.DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        return cursor.rowcount > 0

init_db()