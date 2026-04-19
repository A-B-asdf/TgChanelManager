"""
PostingService с БД (SQLite) для логирования отправленных сообщений.
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, Optional, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Posting Service", version="0.2.0")

# ---------- Конфигурация БД ----------
DB_PATH = os.getenv("POSTING_DB_PATH", "/app/data/posting.db")

def init_db():
    """Инициализирует таблицу sent_messages."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
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
        conn.commit()

init_db()

# ---------- DTO ----------
class PostMessageRequest(BaseModel):
    channel_id: int
    text: str
    parse_mode: Optional[str] = "HTML"

class ChangeMessageRequest(BaseModel):
    new_text: str
    channel_id: Optional[int] = None
    parse_mode: Optional[str] = "HTML"

# ---------- Работа с БД ----------
def log_sent_message(channel_id: int, platform: str, external_id: Optional[int], text_preview: str, status: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO sent_messages (channel_id, platform, external_message_id, text_preview, status) VALUES (?, ?, ?, ?, ?)",
            (channel_id, platform, external_id, text_preview, status)
        )
        conn.commit()

def get_message_logs(limit: int = 100) -> List[Dict]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM sent_messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(row) for row in rows]

# ---------- Функции-заглушки вызовов адаптера ----------
def call_tg_adapter_post_message(channel_id: int, text: str, parse_mode: str) -> Dict:
    """
    Выполняет HTTP-запрос к TgAdapterPostingService: POST /api/post_msg/
    Возвращает ответ адаптера: {"status": "sent", "message_id": ...}
    """
    pass

def call_tg_adapter_change_message(msg_id: int, new_text: str, parse_mode: str, channel_id: Optional[int]) -> Dict:
    """
    Выполняет HTTP-запрос к TgAdapterPostingService: POST /api/change_msg/{msg_id}
    """
    pass

# ---------- API эндпоинты ----------
@app.post("/api/post_msg/", response_model=Dict)
async def post_message(request: PostMessageRequest):
    response = call_tg_adapter_post_message(
        channel_id=request.channel_id,
        text=request.text,
        parse_mode=request.parse_mode or "HTML"
    )
    success = response.get("status") == "sent"
    log_sent_message(
        channel_id=request.channel_id,
        platform="telegram",
        external_id=response.get("message_id"),
        text_preview=request.text[:50],
        status=response.get("status", "failed")
    )
    return {
        "status": "sent" if success else "failed",
        "message_id": response.get("message_id"),
        "channel_id": request.channel_id,
        "text_preview": request.text[:50]
    }

@app.post("/api/change_msg/{msg_id}", response_model=Dict)
async def change_message(msg_id: int, request: ChangeMessageRequest):
    response = call_tg_adapter_change_message(
        msg_id=msg_id,
        new_text=request.new_text,
        parse_mode=request.parse_mode or "HTML",
        channel_id=request.channel_id
    )
    # Здесь можно добавить логирование редактирования
    return {"status": response.get("status"), "message_id": msg_id}

@app.get("/api/logs")
async def get_logs(limit: int = 100):
    return get_message_logs(limit)

# ---------- Запуск ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)