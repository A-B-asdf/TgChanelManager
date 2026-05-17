import os
import sqlite3
from typing import Optional, Dict

from channel_service.core.config import Config


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def init_db():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_channel_id INTEGER NOT NULL UNIQUE,
                tg_access_hash INTEGER,
                title TEXT NOT NULL,
                owner_account_id INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        if not _column_exists(conn, "channels", "tg_access_hash"):
            conn.execute("ALTER TABLE channels ADD COLUMN tg_access_hash INTEGER")


def create_channel_record(tg_channel_id: int, title: str, owner_account_id: int, tg_access_hash: Optional[int] = None) -> int:
    with sqlite3.connect(Config.DB_PATH) as conn:
        cur = conn.execute(
            "INSERT INTO channels (tg_channel_id, tg_access_hash, title, owner_account_id) VALUES (?, ?, ?, ?)",
            (tg_channel_id, tg_access_hash, title, owner_account_id),
        )
        return cur.lastrowid


def get_channel_info_from_db(channel_id: int) -> Optional[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM channels WHERE id = ?", (channel_id,)).fetchone()
        return dict(row) if row else None


def delete_channel_record(channel_id: int) -> bool:
    with sqlite3.connect(Config.DB_PATH) as conn:
        cur = conn.execute("DELETE FROM channels WHERE id = ?", (channel_id,))
        return cur.rowcount > 0


def update_channel_owner(channel_id: int, new_owner_id: int):
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute("UPDATE channels SET owner_account_id = ? WHERE id = ?", (new_owner_id, channel_id))


init_db()
