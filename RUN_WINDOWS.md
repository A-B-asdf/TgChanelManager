# Запуск Telegram-бота на Windows

Ниже два варианта запуска: рекомендуемый через Docker Desktop и отдельный запуск только `ui-bot` из Windows. Для полноценной работы команд `/create_channel`, `/list_channels`, `/schedule`, `/publish_now` должны быть запущены backend-сервисы.

## 1. Подготовка

Установите:

1. Docker Desktop for Windows.
2. Git Bash или PowerShell 7.
3. Python 3.11, если хотите запускать `ui-bot` без Docker.

Создайте файл `.env` в корне проекта на основе `.env.example`:

```env
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_CHANNEL_ACCOUNT_PHONE=+71234567890
TELEGRAM_POSTING_ACCOUNT_PHONE=+71234567890
TELEGRAM_BOT_TOKEN=1234567890:replace_me
PROXY_URL=
PROXY_USER=
PROXY_PASSWORD=
DEFAULT_TIMEZONE=Europe/Moscow
REQUEST_TIMEOUT=20
```

Где взять значения:

- `TELEGRAM_BOT_TOKEN` — в BotFather.
- `TELEGRAM_API_ID` и `TELEGRAM_API_HASH` — в кабинете Telegram API: https://my.telegram.org/apps.
- `TELEGRAM_CHANNEL_ACCOUNT_PHONE` — номер аккаунта Telegram, который будет создавать каналы.
- `TELEGRAM_POSTING_ACCOUNT_PHONE` — номер аккаунта Telegram, который будет публиковать сообщения. Для MVP можно использовать тот же номер.

Если Telegram без прокси не открывается, заполните, например:

```env
PROXY_URL=socks5://127.0.0.1:1080
```

или:

```env
PROXY_URL=socks5://user:password@host:1080
```

## 2. Рекомендуемый запуск всего проекта через Docker

Откройте PowerShell в корне проекта и выполните:

```powershell
docker compose build
```

Перед первым запуском нужно создать Telethon-сессии. Это интерактивный шаг: Telegram пришлёт код подтверждения.

```powershell
docker compose run --rm -it tg-adapter-channel python create_session.py
docker compose run --rm -it tg-adapter-posting python create_session.py
```

После успешного создания сессий запустите все сервисы:

```powershell
docker compose up -d
```

Проверить логи бота:

```powershell
docker compose logs -f ui-bot
```

Остановить проект:

```powershell
docker compose down
```

Остановить проект и удалить базы/сессии из Docker volumes:

```powershell
docker compose down -v
```

## 3. Запуск только Telegram-бота напрямую в Windows

Этот вариант подходит, если backend-сервисы уже запущены отдельно, например через Docker.

В PowerShell из корня проекта:

```powershell
cd ui-bot
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Создайте или используйте корневой `.env`. Для запуска бота из Windows backend-адреса должны указывать на `localhost`, а не на docker service names:

```powershell
$env:TELEGRAM_BOT_TOKEN="1234567890:replace_me"
$env:FULFILLMENT_SERVICE_URL="http://localhost:8003"
$env:CONTENT_SCHEDULER_URL="http://localhost:8000"
# Если нужен прокси:
# $env:PROXY_URL="socks5://127.0.0.1:1080"
python bot.py
```

Если используете `.env`, добавьте туда:

```env
FULFILLMENT_SERVICE_URL=http://localhost:8003
CONTENT_SCHEDULER_URL=http://localhost:8000
```

## 4. Команды бота

- `/start` — справка.
- `/create_channel` — бот попросит название канала и создаст его.
- `/list_channels` — покажет каналы текущего Telegram-пользователя.
- `/schedule 0 12,0 * * *` — установит публикацию по cron.
- `/publish_now` — запустит публикацию сразу.
- `/sell 123` — зарезервирует канал с ID `123`.
- `/cancel` — отменит текущий ввод.

## 5. Частые проблемы

### Бот не отвечает

Проверьте логи:

```powershell
docker compose logs -f ui-bot
```

Проверьте, что токен задан:

```powershell
docker compose config
```

### Ошибка подключения к Telegram

Если вы в сети, где Telegram API заблокирован, задайте `PROXY_URL` в `.env`, пересоберите и перезапустите:

```powershell
docker compose up -d --build
```

### Команда `/create_channel` падает на первом создании

Сначала создайте Telethon-сессии:

```powershell
docker compose run --rm -it tg-adapter-channel python create_session.py
docker compose run --rm -it tg-adapter-posting python create_session.py
```

### Бот из Windows не видит backend

Для запуска `bot.py` напрямую в Windows используйте:

```env
FULFILLMENT_SERVICE_URL=http://localhost:8003
CONTENT_SCHEDULER_URL=http://localhost:8000
```

Внутри Docker должны оставаться адреса:

```env
FULFILLMENT_SERVICE_URL=http://fulfillment-service:8003
CONTENT_SCHEDULER_URL=http://content-scheduler:8000
```
