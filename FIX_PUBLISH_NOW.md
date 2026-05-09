# Исправление publish_now

В этой версии `/publish_now` больше не отвечает сразу `publishing_started`, а реально выполняет публикацию и возвращает результат: сколько сообщений отправлено и какие ошибки произошли.

Ключевое исправление: при создании приватного Telegram-канала теперь сохраняется `access_hash`. Без него второй Telethon-адаптер часто не может найти приватный канал только по числовому `channel_id`, поэтому бот писал «Публикация запущена», а сообщение в канал не приходило.

Если канал был создан старой версией проекта, в базе у него нет `tg_access_hash`. Самый простой способ для проверки — создать новый канал через `/create_channel` уже после обновления, затем нажать `/publish_now`.

После замены файлов пересоберите и перезапустите контейнеры:

```powershell
docker compose down
docker compose build --no-cache
docker compose up -d
```

Посмотреть результат вручную:

```powershell
docker compose logs --tail=100 content-scheduler
docker compose logs --tail=100 posting-service
docker compose logs --tail=100 tg-adapter-posting
```
