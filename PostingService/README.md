# Posting Service

Микросервис для отправки и редактирования сообщений в Telegram (через TgAdapter).

## Эндпоинты
- `POST /api/post_msg/` – отправить сообщение
- `POST /api/change_msg/{msg_id}` – отредактировать сообщение
- `GET /api/logs` – получить лог отправленных сообщений