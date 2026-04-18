"""
Content-Scheduler Service
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional
import uvicorn

# Создаём экземпляр приложения FastAPI
app = FastAPI(
    title="Content-Scheduler Service",
    description="Управляет расписанием публикаций для аккаунтов Telegram",
    version="0.1.0"
)

# DTO
class ScheduleSettings(BaseModel):
    """
    Настройки планирования для аккаунта.
    Передаются в теле POST-запроса на /api/add_account_schedule/{account_id}
    """
    cron: str                     # cron-выражение, например "0 12,0 * * *" (дважды в день: 12:00 и 00:00)
    timezone: str = "Europe/Moscow"  # часовой пояс, по умолчанию московское время
    active: bool = True           # активно ли расписание (можно отключить без удаления)
    # Позже можно добавить: content_source, post_interval и т.д.

#  Вспомогательные внутренние функции 
def save_schedule_to_db(account_id: int, settings: ScheduleSettings) -> int:
    """
    Сохраняет настройки расписания в базу данных (или in-memory хранилище).
    Возвращает уникальный schedule_id.
    В реальной реализации: INSERT INTO schedules (account_id, cron, timezone, active) VALUES (...)
    """
    # Детерминированный stub-id для воспроизводимых тестов
    return int(f"{account_id}{len(settings.cron)}")


def fetch_anekdot_from_source() -> str:
    """
    Парсит страницу https://www.anekdot.ru/last/anekdot/
    Извлекает текст первого (самого свежего) анекдота.
    Возвращает строку с анекдотом.
    При ошибке соединения или парсинга возвращает дефолтный текст:
    "Анекдот не загрузился, но мы работаем над этим."
    """
    return "[stub] Анекдот дня: тестовый контент для планировщика."

def schedule_background_job(schedule_id: int, cron: str, timezone: str) -> Dict:
    """
    Регистрирует задачу в планировщике (например, APScheduler).
    При наступлении времени будет вызвана публикация контента.
    В реальной реализации: добавляем job в планировщик с указанным cron.
    """
    return {
        "status": "scheduled",
        "schedule_id": schedule_id,
        "cron": cron,
        "timezone": timezone,
    }


def publish_for_account(account_id: int) -> Dict:
    """
    Основная задача планировщика для одного аккаунта:
    1. fetch_anekdot_from_source() -> текст
    2. get_channels_by_account(account_id) -> список каналов
    3. Для каждого канала send_via_posting_service()
    Логирует успехи/ошибки.
    """
    content = fetch_anekdot_from_source()
    return {
        "status": "stub",
        "account_id": account_id,
        "generated_content_preview": content[:80],
        "published_channels": 0,
    }

#API эндпоинты
@app.post("/api/add_account_schedule/{account_id}", response_model=Dict)
async def add_account_schedule(account_id: int, settings: ScheduleSettings):
    """
    Добавляет аккаунт в планировщик с заданными настройками.
    - account_id: идентификатор аккаунта из пути (например, 12345)
    - settings: настройки расписания (cron, timezone, active)
    Возвращает schedule_id и подтверждение.
    """
    # Шаг 1: сохраняем настройки в БД
    schedule_id = save_schedule_to_db(account_id, settings)
    
    # Шаг 2: если расписание активно, запускаем фоновую задачу
    scheduling_result = {"status": "inactive"}
    if settings.active:
        scheduling_result = schedule_background_job(schedule_id, settings.cron, settings.timezone)

    # Возвращаем результат
    return {
        "status": "created",
        "account_id": account_id,
        "schedule_id": schedule_id,
        "cron": settings.cron,
        "timezone": settings.timezone,
        "active": settings.active,
        "scheduler": scheduling_result,
    }

#Запуск сервиса
if __name__ == "__main__":
    # Запускаем сервер на 8000 порту
    uvicorn.run(app, host="0.0.0.0", port=8000)
