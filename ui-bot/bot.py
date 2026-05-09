import os
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv
from requests import RequestException
from telegram import BotCommand, KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FULFILLMENT_URL = os.getenv("FULFILLMENT_SERVICE_URL", "http://fulfillment-service:8003")
SCHEDULER_URL = os.getenv("CONTENT_SCHEDULER_URL", "http://content-scheduler:8000")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "20"))
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")


def main_keyboard() -> ReplyKeyboardMarkup:
    """Persistent command keyboard shown under the Telegram input field."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("/create_channel"), KeyboardButton("/list_channels")],
            [KeyboardButton("/publish_now"), KeyboardButton("/schedule 0 12,0 * * *")],
            [KeyboardButton("/status"), KeyboardButton("/help")],
            [KeyboardButton("/cancel")],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Выберите команду или напишите сообщение",
    )


COMMANDS = [
    BotCommand("start", "Показать меню"),
    BotCommand("help", "Помощь и список команд"),
    BotCommand("create_channel", "Создать Telegram-канал"),
    BotCommand("list_channels", "Показать мои каналы"),
    BotCommand("publish_now", "Опубликовать анекдот сейчас"),
    BotCommand("schedule", "Настроить расписание: /schedule 0 12,0 * * *"),
    BotCommand("sell", "Зарезервировать канал: /sell ID"),
    BotCommand("status", "Показать статистику"),
    BotCommand("cancel", "Отменить текущий ввод"),
]


async def setup_bot_commands(app: Application) -> None:
    """Register commands in Telegram's built-in slash-command menu."""
    await app.bot.set_my_commands(COMMANDS)


def _api_get(url: str) -> Dict[str, Any]:
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    return response.json()


def _api_post(url: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    response = requests.post(url, json=payload or {}, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    if response.content:
        return response.json()
    return {}


def _format_api_error(exc: Exception) -> str:
    if isinstance(exc, RequestException) and exc.response is not None:
        try:
            detail = exc.response.json().get("detail")
            if detail:
                return str(detail)
        except Exception:
            pass
        return exc.response.text[:500]
    return str(exc)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я бот для управления каналами.\n\n"
        "Кнопки снизу отправляют обычные команды, поэтому их можно нажимать вместо ручного ввода.\n\n"
        "Основные команды:\n"
        "/create_channel - создать новый канал\n"
        "/list_channels - список моих каналов\n"
        "/schedule <cron> - настроить автопостинг, например: /schedule 0 12,0 * * *\n"
        "/publish_now - сразу опубликовать анекдот в мои каналы\n"
        "/sell <channel_id> - зарезервировать канал для продажи\n"
        "/status - статистика\n"
        "/cancel - отменить текущий ввод",
        reply_markup=main_keyboard(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Операция отменена.", reply_markup=main_keyboard())


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_channel_title"):
        await update.message.reply_text("Неизвестная команда. Используйте /start", reply_markup=main_keyboard())
        return

    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text(
            "Название не должно быть пустым. Введите название канала или /cancel.",
            reply_markup=main_keyboard(),
        )
        return

    user_id = update.effective_user.id
    try:
        data = _api_post(
            f"{FULFILLMENT_URL}/api/create_channel",
            {"title": title, "description": "", "account_id": user_id},
        )
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Не удалось создать канал: {_format_api_error(exc)}",
            reply_markup=main_keyboard(),
        )
        return

    context.user_data.pop("awaiting_channel_title", None)
    channel_id = data.get("channel_id")
    tg_channel_id = data.get("tg_channel_id")
    suffix = f"\nTelegram ID: {tg_channel_id}" if tg_channel_id else ""
    await update.message.reply_text(f"✅ Канал создан! ID: {channel_id}{suffix}", reply_markup=main_keyboard())


async def create_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["awaiting_channel_title"] = True
    await update.message.reply_text("Введите название канала или /cancel для отмены:", reply_markup=main_keyboard())


async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        data = _api_get(f"{FULFILLMENT_URL}/api/get_all_channel?account_id={user_id}")
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Не удалось получить список каналов: {_format_api_error(exc)}",
            reply_markup=main_keyboard(),
        )
        return

    channels = data.get("items", [])
    if not channels:
        await update.message.reply_text("У вас пока нет каналов.", reply_markup=main_keyboard())
        return

    text = "📢 Ваши каналы:\n"
    for ch in channels:
        booked = " — забронирован" if ch.get("is_booked") else ""
        text += f"• ID {ch['id']}: {ch['title']}{booked}\n"
    await update.message.reply_text(text, reply_markup=main_keyboard())


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cron = " ".join(context.args).strip().strip('"').strip("'")
    if not cron:
        await update.message.reply_text(
            "Использование: /schedule 0 12,0 * * *\n\n"
            "Можно нажать кнопку с готовым расписанием: два раза в день, в 12:00 и 00:00.",
            reply_markup=main_keyboard(),
        )
        return

    user_id = update.effective_user.id
    try:
        _api_post(
            f"{SCHEDULER_URL}/api/add_account_schedule/{user_id}",
            {"cron": cron, "timezone": DEFAULT_TIMEZONE, "active": True},
        )
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Ошибка при установке расписания: {_format_api_error(exc)}",
            reply_markup=main_keyboard(),
        )
        return

    await update.message.reply_text(f"⏰ Расписание {cron} установлено для ваших каналов.", reply_markup=main_keyboard())


async def publish_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        data = _api_post(f"{SCHEDULER_URL}/api/publish_now/{user_id}")
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Не удалось выполнить публикацию: {_format_api_error(exc)}",
            reply_markup=main_keyboard(),
        )
        return

    sent = data.get("sent", 0)
    failed = data.get("failed", 0)
    status = data.get("status", "unknown")
    errors = data.get("errors") or []
    if sent and not failed:
        await update.message.reply_text(f"✅ Опубликовано: {sent}. Статус: {status}", reply_markup=main_keyboard())
    elif sent or failed:
        details = "\n".join(str(e)[:500] for e in errors[:3])
        await update.message.reply_text(
            f"⚠️ Публикация завершена: отправлено {sent}, ошибок {failed}.\n{details}",
            reply_markup=main_keyboard(),
        )
    else:
        details = "\n".join(str(e)[:500] for e in errors[:3]) or "Причина не указана. Проверьте логи content-scheduler."
        await update.message.reply_text(
            f"❌ Ничего не опубликовано. Статус: {status}.\n{details}",
            reply_markup=main_keyboard(),
        )


async def sell_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Укажите ID канала: /sell 123", reply_markup=main_keyboard())
        return

    try:
        channel_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("ID канала должен быть числом: /sell 123", reply_markup=main_keyboard())
        return

    user_id = update.effective_user.id
    try:
        _api_post(f"{FULFILLMENT_URL}/api/book_channel/{channel_id}", {"account_id": user_id})
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Не удалось забронировать канал: {_format_api_error(exc)}",
            reply_markup=main_keyboard(),
        )
        return

    await update.message.reply_text(f"🛒 Канал {channel_id} зарезервирован для продажи.", reply_markup=main_keyboard())


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Статистика пока в разработке.", reply_markup=main_keyboard())


def build_request():
    proxy_url = os.getenv("PROXY_URL")
    if not proxy_url:
        return None

    request_kwargs: Dict[str, Any] = {"proxy_url": proxy_url}
    if os.getenv("PROXY_USER") and os.getenv("PROXY_PASSWORD"):
        request_kwargs["urllib3_proxy_kwargs"] = {
            "username": os.getenv("PROXY_USER"),
            "password": os.getenv("PROXY_PASSWORD"),
        }
    return HTTPXRequest(**request_kwargs)


def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set")

    builder = Application.builder().token(token).post_init(setup_bot_commands)
    request = build_request()
    if request:
        builder = builder.request(request)
    app = builder.build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("create_channel", create_channel))
    app.add_handler(CommandHandler("list_channels", list_channels))
    app.add_handler(CommandHandler("schedule", schedule_command))
    app.add_handler(CommandHandler("publish_now", publish_now))
    app.add_handler(CommandHandler("sell", sell_channel))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
