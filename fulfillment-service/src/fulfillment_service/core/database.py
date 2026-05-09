import os
import sqlite3
from typing import Dict, List, Optional

from fulfillment_service.core.config import Config


def _column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row[1] == column for row in rows)


def init_db():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL UNIQUE,
                tg_channel_id INTEGER,
                tg_access_hash INTEGER,
                title TEXT NOT NULL,
                owner_account_id INTEGER NOT NULL,
                is_booked BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        if not _column_exists(conn, "channels", "tg_channel_id"):
            conn.execute("ALTER TABLE channels ADD COLUMN tg_channel_id INTEGER")
        if not _column_exists(conn, "channels", "tg_access_hash"):
            conn.execute("ALTER TABLE channels ADD COLUMN tg_access_hash INTEGER")


def get_all_channels_db(account_id: Optional[int] = None) -> List[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        if account_id is None:
            rows = conn.execute("SELECT * FROM channels ORDER BY id DESC").fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM channels WHERE owner_account_id = ? ORDER BY id DESC",
                (account_id,),
            ).fetchall()
        return [dict(row) for row in rows]


def get_channel_by_id_db(id: int) -> Optional[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM channels WHERE id = ?", (id,)).fetchone()
        return dict(row) if row else None


def filter_channels_db(filters: dict) -> List[Dict]:
    account_id = filters.get("account_id")
    return get_all_channels_db(account_id=account_id)


def book_channel_db(id: int, owner_account_id: Optional[int] = None) -> bool:
    with sqlite3.connect(Config.DB_PATH) as conn:
        if owner_account_id is None:
            cur = conn.execute(
                "UPDATE channels SET is_booked = 1 WHERE id = ? AND is_booked = 0",
                (id,),
            )
        else:
            cur = conn.execute(
                """
                UPDATE channels
                SET is_booked = 1
                WHERE id = ? AND owner_account_id = ? AND is_booked = 0
                """,
                (id, owner_account_id),
            )
        return cur.rowcount > 0


def create_channel_record(channel_service_id: int, tg_channel_id: int, title: str, owner_account_id: int, tg_access_hash: Optional[int] = None):
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute(
            """
            INSERT INTO channels (channel_id, tg_channel_id, tg_access_hash, title, owner_account_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (channel_service_id, tg_channel_id, tg_access_hash, title, owner_account_id),
        )


def update_channel_owner_db(id: int, new_owner_id: int):
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute(
            "UPDATE channels SET owner_account_id = ?, is_booked = 0 WHERE id = ?",
            (new_owner_id, id),
        )


init_db()
