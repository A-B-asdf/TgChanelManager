# Content-Scheduler Service

Микросервис для планирования публикации анекдотов в Telegram-каналы.

## Эндпоинты
- `POST /api/add_account_schedule/{account_id}` – добавить расписание
- `GET /api/schedules/{account_id}` – получить расписания аккаунта
- `DELETE /api/schedule/{schedule_id}` – удалить расписание

## Переменные окружения
- `SCHEDULER_DB_PATH` – путь к SQLite БД
- `POSTING_SERVICE_URL` – URL сервиса постинга
- `CRON_SCHEDULE` – cron-выражение (по умолчанию 0 12,0 * * *)
- `TIMEZONE` – часовой пояс