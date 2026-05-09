import os
import sqlite3
from typing import Dict, List, Optional

from posting_service.core.config import Config

def init_db():
    os.makedirs(os.path.dirname(Config.DB_PATH), exist_ok=True)
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id INTEGER NOT NULL,
                platform TEXT NOT NULL DEFAULT 'telegram',
                external_message_id INTEGER,
                text_preview TEXT,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
    conn.close()

def log_sent_message(channel_id: int, platform: str, external_id: Optional[int], text_preview: str, status: str):
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.execute(
            "INSERT INTO sent_messages (channel_id, platform, external_message_id, text_preview, status) VALUES (?, ?, ?, ?, ?)",
            (channel_id, platform, external_id, text_preview, status)
        )

def get_message_logs(limit: int = 100) -> List[Dict]:
    with sqlite3.connect(Config.DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM sent_messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

init_db()
