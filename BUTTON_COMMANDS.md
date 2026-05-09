# Кнопки-команды Telegram-бота

В этой версии бот показывает постоянную клавиатуру под полем ввода Telegram и регистрирует команды в системном меню Telegram.

## Что добавлено

- Постоянные кнопки:
  - `/create_channel`
  - `/list_channels`
  - `/publish_now`
  - `/schedule 0 12,0 * * *`
  - `/status`
  - `/help`
  - `/cancel`
- Команды также появляются в Telegram-меню `/`.
- Добавлена команда `/menu` как синоним `/start`, чтобы заново показать клавиатуру.

## Как применить обновление

```powershell
docker compose down
docker compose build --no-cache ui-bot
docker compose up -d
```

После запуска откройте бота в Telegram и отправьте:

```text
/start
```

Если клавиатура не появилась сразу, закройте и снова откройте чат с ботом или отправьте `/menu`.
