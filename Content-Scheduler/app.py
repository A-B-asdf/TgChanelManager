"""
Content-Scheduler Service с БД (SQLite) для хранения расписаний.
"""

import os
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Content-Scheduler Service", version="0.2.0")

# ---------- Конфигурация БД ----------
DB_PATH = os.getenv("SCHEDULER_DB_PATH", "/app/data/scheduler.db")

def init_db():
    """Инициализирует таблицу schedules."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
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

init_db()

# ---------- DTO ----------
class ScheduleSettings(BaseModel):
    cron: str
    timezone: str = "Europe/Moscow"
    active: bool = True

# ---------- Работа с БД ----------
def save_schedule_to_db(account_id: int, settings: ScheduleSettings) -> int:
    """Сохраняет расписание и возвращает schedule_id."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute(
            "INSERT INTO schedules (account_id, cron, timezone, active) VALUES (?, ?, ?, ?)",
            (account_id, settings.cron, settings.timezone, settings.active)
        )
        return cursor.lastrowid

def get_schedules_by_account(account_id: int) -> List[Dict]:
    """Возвращает все расписания аккаунта."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM schedules WHERE account_id = ?", (account_id,)).fetchall()
        return [dict(row) for row in rows]

def delete_schedule(schedule_id: int) -> bool:
    """Удаляет расписание по id."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
        return cursor.rowcount > 0

# ---------- Вспомогательные функции (заглушки) ----------
def fetch_anekdot_from_source() -> str:
    """
    Парсит страницу https://www.anekdot.ru/last/anekdot/
    Извлекает текст первого анекдота.
    Возвращает строку с анекдотом.
    """
    pass

def get_channels_by_account(account_id: int) -> List[int]:
    """
    Запрашивает у FulfillmentService или ChanelService список каналов,
    принадлежащих аккаунту.
    Возвращает list channel_id.
    """
    pass

def send_via_posting_service(channel_id: int, text: str) -> Dict:
    """
    Вызывает PostingService: POST /api/post_msg/
    Тело: {"channel_id": channel_id, "text": text, "parse_mode": "HTML"}
    """
    pass

def schedule_background_job(schedule_id: int, cron: str, timezone: str):
    """
    Регистрирует задачу в планировщике (APScheduler).
    При наступлении времени вызывает publish_for_account.
    """
    pass

def publish_for_account(account_id: int):
    """
    Основная задача планировщика:
    1. fetch_anekdot_from_source() -> текст
    2. get_channels_by_account(account_id) -> список каналов
    3. Для каждого канала send_via_posting_service()
    """
    pass

# ---------- API эндпоинты ----------
@app.post("/api/add_account_schedule/{account_id}", response_model=Dict)
async def add_account_schedule(account_id: int, settings: ScheduleSettings):
    schedule_id = save_schedule_to_db(account_id, settings)
    if settings.active:
        schedule_background_job(schedule_id, settings.cron, settings.timezone)
    return {
        "status": "created",
        "account_id": account_id,
        "schedule_id": schedule_id,
        "cron": settings.cron,
        "active": settings.active
    }

@app.get("/api/schedules/{account_id}")
async def get_schedules(account_id: int):
    return get_schedules_by_account(account_id)

@app.delete("/api/schedule/{schedule_id}")
async def remove_schedule(schedule_id: int):
    if delete_schedule(schedule_id):
        return {"status": "deleted", "schedule_id": schedule_id}
    raise HTTPException(status_code=404, detail="Schedule not found")

# ---------- Запуск ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)