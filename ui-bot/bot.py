import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import requests
from dotenv import load_dotenv
from requests import RequestException
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

load_dotenv()
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

FULFILLMENT_URL = os.getenv("FULFILLMENT_SERVICE_URL", "http://fulfillment-service:8003")
SCHEDULER_URL = os.getenv("CONTENT_SCHEDULER_URL", "http://content-scheduler:8000")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "120"))
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")
HOURLY_CRON = os.getenv("HOURLY_CRON", "0 * * * *")

CONTENT_TYPES: Dict[str, str] = {
    "jokes": "Анекдоты",
    "news": "Новости",
    "sport": "Спорт",
    "games": "Игры",
    "recipes": "Рецепты",
    "memes": "Мемы",
    "cats": "Котики",
    "music": "Музыка",
}


def content_type_label(value: Optional[str]) -> str:
    return CONTENT_TYPES.get((value or "jokes").strip().lower(), CONTENT_TYPES["jokes"])


def content_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("😂 Анекдоты", callback_data="create_type:jokes"), InlineKeyboardButton("📰 Новости", callback_data="create_type:news")],
            [InlineKeyboardButton("🏆 Спорт", callback_data="create_type:sport"), InlineKeyboardButton("🎮 Игры", callback_data="create_type:games")],
            [InlineKeyboardButton("🍽 Рецепты", callback_data="create_type:recipes"), InlineKeyboardButton("🤣 Мемы", callback_data="create_type:memes")],
            [InlineKeyboardButton("🐱 Котики", callback_data="create_type:cats"), InlineKeyboardButton("🎵 Музыка", callback_data="create_type:music")],
        ]
    )


def _parse_admin_ids() -> Set[int]:
    raw = os.getenv("ADMIN_USER_IDS", "").strip()
    ids: Set[int] = set()
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            pass
    return ids


ADMIN_USER_IDS = _parse_admin_ids()


def is_admin(user_id: Optional[int]) -> bool:
    # Для локальной демонстрации: если ADMIN_USER_IDS пустой, все считаются админами.
    # Для реального режима обязательно заполните ADMIN_USER_IDS в .env.
    return bool(user_id) and (not ADMIN_USER_IDS or user_id in ADMIN_USER_IDS)


ADMIN_BTN_CREATE = "➕ Создать канал"
ADMIN_BTN_PUBLISH = "🚀 Опубликовать"
ADMIN_BTN_STATUS = "📊 Статусы"
ADMIN_BTN_HELP = "ℹ️ Помощь"

USER_BTN_GET = "🎁 Получить канал"
USER_BTN_CONFIRM = "✅ Я вошёл"
USER_BTN_MY = "📢 Мой канал"
USER_BTN_HELP = "ℹ️ Помощь"


def admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(ADMIN_BTN_CREATE), KeyboardButton(ADMIN_BTN_PUBLISH)],
            [KeyboardButton(ADMIN_BTN_STATUS), KeyboardButton(ADMIN_BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Админ-меню",
    )


def user_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(USER_BTN_GET)],
            [KeyboardButton(USER_BTN_CONFIRM), KeyboardButton(USER_BTN_MY)],
            [KeyboardButton(USER_BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Получить свободный канал",
    )


def keyboard_for(user_id: Optional[int]) -> ReplyKeyboardMarkup:
    return admin_keyboard() if is_admin(user_id) else user_keyboard()


COMMANDS = [
    BotCommand("start", "Показать меню"),
    BotCommand("menu", "Показать кнопки"),
    BotCommand("help", "Помощь"),
    BotCommand("whoami", "Показать мой Telegram ID"),
    BotCommand("get_channel", "Пользователь: получить свободный канал"),
    BotCommand("confirm_joined", "Пользователь: подтвердить вход"),
    BotCommand("my_channel", "Пользователь: мой канал"),
    BotCommand("create_channel", "Админ: создать канал"),
    BotCommand("publish_now", "Админ: опубликовать сейчас"),
    BotCommand("schedule", "Админ: настроить автопостинг"),
    BotCommand("status", "Админ: вкладка статусов"),
    BotCommand("delete_channel", "Админ: удалить канал"),
    BotCommand("cancel", "Отменить текущий ввод"),
]


async def setup_bot_commands(app: Application) -> None:
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



def _ensure_admin_hourly_schedule(user_id: int) -> Optional[Dict[str, Any]]:
    try:
        return _api_post(f"{SCHEDULER_URL}/api/ensure_hourly_schedule/{user_id}")
    except Exception:
        return None

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


def _user_label(user) -> str:
    if not user:
        return "unknown"
    if user.username:
        return f"@{user.username}"
    name = " ".join(x for x in [user.first_name, user.last_name] if x)
    return name or str(user.id)


def _channel_lines(channels: List[Dict[str, Any]]) -> str:
    if not channels:
        return "Каналов пока нет."
    lines = []
    for ch in channels:
        ctype = content_type_label(ch.get("content_type"))
        if ch.get("is_booked"):
            assigned = ch.get("assigned_account_id") or "неизвестно"
            handoff = ch.get("handoff_status") or "claimed"
            status = f"занят пользователем {assigned}, передача: {handoff}"
        else:
            status = "свободен"
        lines.append(f"• ID {ch['id']}: {ch['title']} — {status}; тип: {ctype}")
    return "\n".join(lines)


async def _notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    for admin_id in ADMIN_USER_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text)
        except TelegramError:
            continue


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_admin(user_id):
        ensured = _ensure_admin_hourly_schedule(user_id)
        ensured_line = ""
        if ensured:
            ensured_line = f"\n✅ Ежечасный автопостинг проверен: {ensured.get('cron')} ({ensured.get('timezone')}).\n"
        text = (
            "👋 Админ-режим включён.\n\n"
            "Вы управляете пулом каналов: создаёте каналы, запускаете ручной постинг "
            "и контролируете автопостинг.\n"
            f"{ensured_line}\n"
            "Основное меню теперь укорочено:\n"
            f"• {ADMIN_BTN_CREATE} — создать приватный канал и выбрать тип контента.\n"
            f"• {ADMIN_BTN_PUBLISH} — опубликовать контент по типам каналов.\n"
            f"• {ADMIN_BTN_STATUS} — отдельная вкладка со статусом каналов, автопостинга и удалением каналов.\n\n"
            "Когда обычный пользователь займёт канал, админу придёт уведомление с названием канала и ID пользователя.\n\n"
            "Важно: для реального режима заполните ADMIN_USER_IDS в .env. Узнать ID можно через /whoami."
        )
    else:
        text = (
            "👋 Привет! Это бот доступа к свободному Telegram-каналу.\n\n"
            f"Нажмите {USER_BTN_GET} — я автоматически выдам первый свободный канал и пришлю ссылку-приглашение. "
            f"После входа в канал нажмите {USER_BTN_CONFIRM}: я выдам вам права администратора и попробую вывести админский аккаунт из канала. "
            f"Если канал уже выдан вам раньше, кнопка {USER_BTN_MY} покажет ссылку повторно."
        )
    await update.message.reply_text(text, reply_markup=keyboard_for(user_id))


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Ваш Telegram ID: {user.id}\nUsername: @{user.username or '-'}\nРоль: {'admin' if is_admin(user.id) else 'user'}",
        reply_markup=keyboard_for(user.id),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Операция отменена.", reply_markup=keyboard_for(update.effective_user.id))


async def require_admin(update: Update) -> bool:
    user_id = update.effective_user.id if update.effective_user else None
    if is_admin(user_id):
        return True
    if update.message:
        await update.message.reply_text("⛔ Эта команда доступна только админу.", reply_markup=keyboard_for(user_id))
    elif update.callback_query:
        await update.callback_query.answer("Команда доступна только админу", show_alert=True)
    return False


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if not context.user_data.get("awaiting_channel_title"):
        if text == ADMIN_BTN_CREATE:
            await create_channel(update, context)
            return
        if text == ADMIN_BTN_PUBLISH:
            await publish_now(update, context)
            return
        if text == ADMIN_BTN_STATUS:
            await status_panel(update, context)
            return
        if text in {ADMIN_BTN_HELP, USER_BTN_HELP}:
            await start(update, context)
            return
        if text == USER_BTN_GET:
            await get_channel(update, context)
            return
        if text == USER_BTN_CONFIRM:
            await confirm_joined(update, context)
            return
        if text == USER_BTN_MY:
            await my_channel(update, context)
            return
        await update.message.reply_text("Неизвестная команда. Используйте /start", reply_markup=keyboard_for(user_id))
        return

    if not is_admin(user_id):
        context.user_data.pop("awaiting_channel_title", None)
        context.user_data.pop("new_channel_content_type", None)
        await update.message.reply_text("⛔ Создавать каналы может только админ.", reply_markup=keyboard_for(user_id))
        return

    content_type = context.user_data.get("new_channel_content_type")
    if not content_type:
        context.user_data.pop("awaiting_channel_title", None)
        await update.message.reply_text(
            "Сначала выберите тип канала.",
            reply_markup=content_type_keyboard(),
        )
        return

    title = text
    if not title:
        await update.message.reply_text(
            "Название не должно быть пустым. Введите название канала или /cancel.",
            reply_markup=keyboard_for(user_id),
        )
        return

    try:
        data = _api_post(
            f"{FULFILLMENT_URL}/api/create_channel",
            {
                "title": title,
                "description": f"Тип контента: {content_type_label(content_type)}",
                "account_id": user_id,
                "content_type": content_type,
            },
        )
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Не удалось создать канал: {_format_api_error(exc)}",
            reply_markup=keyboard_for(user_id),
        )
        return

    context.user_data.pop("awaiting_channel_title", None)
    context.user_data.pop("new_channel_content_type", None)
    channel_id = data.get("channel_id")
    tg_channel_id = data.get("tg_channel_id")
    returned_type = data.get("content_type") or content_type
    suffix = f"\nTelegram ID: {tg_channel_id}" if tg_channel_id else ""
    await update.message.reply_text(
        f"✅ Канал создан и добавлен в свободный пул.\nТип: {content_type_label(returned_type)}\nID в базе: {channel_id}{suffix}",
        reply_markup=keyboard_for(user_id),
    )


async def create_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    context.user_data.pop("awaiting_channel_title", None)
    context.user_data.pop("new_channel_content_type", None)
    await update.message.reply_text(
        "Выберите тип контента для нового канала:",
        reply_markup=content_type_keyboard(),
    )


async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    user_id = update.effective_user.id
    try:
        data = _api_get(f"{FULFILLMENT_URL}/api/get_all_channel?account_id={user_id}")
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Не удалось получить список каналов: {_format_api_error(exc)}",
            reply_markup=keyboard_for(user_id),
        )
        return

    channels = data.get("items", [])
    await update.message.reply_text("📢 Ваши каналы:\n" + _channel_lines(channels), reply_markup=keyboard_for(user_id))


async def available_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        data = _api_get(f"{FULFILLMENT_URL}/api/get_available_channels")
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Не удалось получить список свободных каналов: {_format_api_error(exc)}",
            reply_markup=keyboard_for(user_id),
        )
        return

    channels = data.get("items", [])
    if is_admin(user_id):
        await update.message.reply_text("🟢 Свободные каналы:\n" + _channel_lines(channels), reply_markup=keyboard_for(user_id))
        return

    if not channels:
        await update.message.reply_text("Пока нет свободных каналов.", reply_markup=keyboard_for(user_id))
        return

    markup = InlineKeyboardMarkup([[InlineKeyboardButton("✅ Получить свободный канал", callback_data="claim_channel:0")]])
    await update.message.reply_text(
        f"Сейчас свободных каналов: {len(channels)}. Нажмите кнопку, чтобы получить первый свободный канал.",
        reply_markup=markup,
    )


async def get_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    target = update.callback_query.message if update.callback_query else update.message

    if is_admin(user_id):
        await target.reply_text(
            "Вы админ, поэтому не забираю канал на вас. Для проверки пользовательского режима зайдите в бота с другого аккаунта.",
            reply_markup=keyboard_for(user_id),
        )
        return

    try:
        data = _api_post(
            f"{FULFILLMENT_URL}/api/claim_available_channel",
            {
                "requester_account_id": user_id,
                "requester_username": user.username,
                "requester_name": _user_label(user),
            },
        )
    except Exception as exc:
        await target.reply_text(
            f"❌ Не удалось выдать канал: {_format_api_error(exc)}",
            reply_markup=keyboard_for(user_id),
        )
        return

    status = data.get("status")
    title = data.get("channel_title") or "канал"
    content_type = data.get("content_type") or "jokes"
    channel_id = data.get("channel_id")
    invite = data.get("invite_link")
    if status == "already_claimed":
        handoff = data.get("handoff_status") or "claimed"
        text = (
            f"ℹ️ Вам уже выдан канал «{title}» (ID {channel_id}).\n"
            f"Тип канала: {content_type_label(content_type)}.\n"
            f"Статус передачи: {handoff}.\n"
            f"Ссылка: {invite}\n\n"
            "Если вы уже вошли в канал, нажмите /confirm_joined."
        )
    else:
        text = (
            f"✅ Вам выдан свободный канал «{title}» (ID {channel_id}).\n"
            f"Тип канала: {content_type_label(content_type)}.\n"
            f"Ссылка для входа: {invite}\n\n"
            "Теперь откройте ссылку, вступите в канал и нажмите /confirm_joined. "
            "После этого я выдам вам права администратора и попробую вывести админский аккаунт из канала."
        )
        await _notify_admins(
            context,
            "🔔 Канал заняли только что\n"
            f"Канал: «{title}» (ID {channel_id})\n"
            f"Тип: {content_type_label(content_type)}\n"
            f"Пользователь: {_user_label(user)} (ID {user_id})\n"
            "Статус: канал помечен занятым, пользователь получил invite-ссылку.",
        )
    await target.reply_text(text, reply_markup=keyboard_for(user_id))


async def my_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        data = _api_get(f"{FULFILLMENT_URL}/api/my_channel/{user_id}")
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Канал пока не выдан: {_format_api_error(exc)}",
            reply_markup=keyboard_for(user_id),
        )
        return

    ch = data.get("channel") or {}
    await update.message.reply_text(
        f"📢 Ваш канал: {ch.get('title')}\n"
        f"Тип: {content_type_label(ch.get('content_type'))}\n"
        f"ID: {ch.get('id')}\n"
        f"Статус передачи: {ch.get('handoff_status') or 'claimed'}\n"
        f"Ссылка: {ch.get('invite_link')}\n\n"
        "Если вы уже вступили в канал, нажмите /confirm_joined.",
        reply_markup=keyboard_for(user_id),
    )


async def confirm_joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    target = update.callback_query.message if update.callback_query else update.message

    if is_admin(user_id):
        await target.reply_text(
            "Вы админ. Команда /confirm_joined нужна только обычному пользователю, который забрал канал.",
            reply_markup=keyboard_for(user_id),
        )
        return

    try:
        data = _api_post(
            f"{FULFILLMENT_URL}/api/finalize_channel_claim",
            {"requester_account_id": user_id, "leave_after_admin": True},
        )
    except Exception as exc:
        await target.reply_text(
            "❌ Пока не получилось завершить передачу.\n\n"
            "Проверьте, что вы уже открыли invite-ссылку и вступили в канал, потом нажмите /confirm_joined ещё раз.\n\n"
            f"Техническая ошибка: {_format_api_error(exc)}",
            reply_markup=keyboard_for(user_id),
        )
        return

    title = data.get("channel_title") or "канал"
    status = data.get("status")
    telegram = data.get("telegram") or {}
    admin_left = bool(telegram.get("admin_left"))
    leave_error = telegram.get("leave_error") or data.get("handoff_error")

    if status in {"completed", "already_completed"} or admin_left:
        text = (
            f"✅ Передача канала «{title}» завершена.\n"
            "Вам выданы права администратора, админский аккаунт вышел из канала."
        )
        await _notify_admins(
            context,
            f"✅ Передача завершена: пользователь {_user_label(user)} (ID {user_id}) теперь админ канала «{title}», админский аккаунт вышел.",
        )
    elif status == "promoted_admin_not_left":
        text = (
            f"⚠️ Вам выданы права администратора в канале «{title}», но Telegram не дал автоматически вывести админский аккаунт.\n"
            f"Ошибка выхода: {leave_error or 'не указана'}\n\n"
            "Канал уже у вас в управлении, но админу нужно вручную выйти или выполнить полноценную передачу владельца в Telegram."
        )
        await _notify_admins(
            context,
            f"⚠️ Пользователь {_user_label(user)} (ID {user_id}) получил админские права в «{title}», но авто-выход админа не сработал: {leave_error}",
        )
    else:
        text = f"⚠️ Неожиданный статус передачи: {status}. Проверьте логи fulfillment-service и tg-adapter-channel."

    await target.reply_text(text, reply_markup=keyboard_for(user_id))


async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    cron = " ".join(context.args).strip().strip('"').strip("'")
    user_id = update.effective_user.id
    if not cron:
        await update.message.reply_text(
            f"Использование: /schedule {HOURLY_CRON}\n\n"
            "Готовая кнопка включает автопостинг каждый час. При установке нового активного расписания старые активные расписания этого админа отключаются.",
            reply_markup=keyboard_for(user_id),
        )
        return

    try:
        data = _api_post(
            f"{SCHEDULER_URL}/api/add_account_schedule/{user_id}",
            {"cron": cron, "timezone": DEFAULT_TIMEZONE, "active": True},
        )
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Ошибка при установке расписания: {_format_api_error(exc)}",
            reply_markup=keyboard_for(user_id),
        )
        return

    await update.message.reply_text(
        f"⏰ Расписание {data.get('cron', cron)} установлено. Проверка и публикация будут выполняться каждый час, пока компьютер/сервер включён.",
        reply_markup=keyboard_for(user_id),
    )


async def publish_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    user_id = update.effective_user.id
    try:
        data = _api_post(f"{SCHEDULER_URL}/api/publish_now/{user_id}")
    except Exception as exc:
        await update.message.reply_text(
            f"❌ Не удалось выполнить публикацию: {_format_api_error(exc)}",
            reply_markup=keyboard_for(user_id),
        )
        return

    sent = data.get("sent", 0)
    failed = data.get("failed", 0)
    status = data.get("status", "unknown")
    errors = data.get("errors") or []
    if sent and not failed:
        type_lines = []
        for item in (data.get("results") or [])[:5]:
            title = item.get("channel_title") or "канал"
            label = item.get("content_type_label") or content_type_label(item.get("content_type"))
            type_lines.append(f"• {title}: {label}")
        extra = "\n" + "\n".join(type_lines) if type_lines else ""
        await update.message.reply_text(f"✅ Опубликовано: {sent}. Статус: {status}{extra}", reply_markup=keyboard_for(user_id))
    elif sent or failed:
        details = "\n".join(str(e)[:500] for e in errors[:3])
        await update.message.reply_text(
            f"⚠️ Публикация завершена: отправлено {sent}, ошибок {failed}.\n{details}",
            reply_markup=keyboard_for(user_id),
        )
    else:
        details = "\n".join(str(e)[:500] for e in errors[:3]) or "Причина не указана. Проверьте логи content-scheduler."
        await update.message.reply_text(
            f"❌ Ничего не опубликовано. Статус: {status}.\n{details}",
            reply_markup=keyboard_for(user_id),
        )


def _short_title(title: Optional[str], limit: int = 32) -> str:
    title = title or "без названия"
    return title if len(title) <= limit else title[: limit - 1] + "…"


async def delete_channel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        if update.callback_query:
            await update.callback_query.message.reply_text("⛔ Удалять каналы может только админ.", reply_markup=keyboard_for(user_id))
        else:
            await update.message.reply_text("⛔ Удалять каналы может только админ.", reply_markup=keyboard_for(user_id))
        return

    target = update.callback_query.message if update.callback_query else update.message
    try:
        data = _api_get(f"{FULFILLMENT_URL}/api/get_all_channel?account_id={user_id}")
        channels = data.get("items", [])
    except Exception as exc:
        await target.reply_text(f"❌ Не удалось получить список каналов: {_format_api_error(exc)}", reply_markup=keyboard_for(user_id))
        return

    if not channels:
        await target.reply_text("Удалять нечего: у вас пока нет каналов.", reply_markup=keyboard_for(user_id))
        return

    rows = []
    for ch in channels:
        status = "занят" if ch.get("is_booked") else "свободен"
        label = f"🗑 ID {ch['id']}: {_short_title(ch.get('title'))} · {content_type_label(ch.get('content_type'))} · {status}"
        rows.append([InlineKeyboardButton(label, callback_data=f"delete_channel:{ch['id']}")])
    rows.append([InlineKeyboardButton("↩️ Назад к статусам", callback_data="status_full:0")])
    await target.reply_text(
        "🗑 Удаление каналов\n\n"
        "Выберите канал. После выбора я покажу подтверждение.\n"
        "Можно удалить канал полностью в Telegram и базе проекта или только убрать его из базы проекта.",
        reply_markup=InlineKeyboardMarkup(rows),
    )


async def delete_channel_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.callback_query.message.reply_text("⛔ Удалять каналы может только админ.", reply_markup=keyboard_for(user_id))
        return
    target = update.callback_query.message if update.callback_query else update.message
    try:
        data = _api_get(f"{FULFILLMENT_URL}/api/get_channel/{channel_id}")
        ch = data.get("channel") or {}
    except Exception as exc:
        await target.reply_text(f"❌ Канал не найден: {_format_api_error(exc)}", reply_markup=keyboard_for(user_id))
        return

    if ch.get("owner_account_id") != user_id:
        await target.reply_text("⛔ Этот канал не принадлежит текущему админу.", reply_markup=keyboard_for(user_id))
        return

    status = "занят" if ch.get("is_booked") else "свободен"
    assigned = ch.get("assigned_account_id") or "—"
    text = (
        "⚠️ Подтвердите удаление канала\n\n"
        f"ID: {ch.get('id')}\n"
        f"Название: {ch.get('title')}\n"
        f"Тип: {content_type_label(ch.get('content_type'))}\n"
        f"Статус: {status}\n"
        f"Пользователь: {assigned}\n\n"
        "Полное удаление попытается удалить канал в Telegram. Это сработает только если админский аккаунт ещё имеет права владельца/админа.\n"
        "Удаление только из базы уберёт канал из менеджера, но сам Telegram-канал останется."
    )
    markup = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Удалить в Telegram и базе", callback_data=f"delete_channel_tg:{channel_id}")],
            [InlineKeyboardButton("🗂 Удалить только из базы", callback_data=f"delete_channel_meta:{channel_id}")],
            [InlineKeyboardButton("❌ Отмена", callback_data="delete_cancel:0")],
        ]
    )
    await target.reply_text(text, reply_markup=markup)


async def delete_channel_execute(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    channel_id: int,
    delete_in_telegram: bool,
    force_metadata_delete: bool,
):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.callback_query.message.reply_text("⛔ Удалять каналы может только админ.", reply_markup=keyboard_for(user_id))
        return
    target = update.callback_query.message if update.callback_query else update.message
    try:
        data = _api_post(
            f"{FULFILLMENT_URL}/api/delete_channel/{channel_id}",
            {
                "account_id": user_id,
                "delete_in_telegram": delete_in_telegram,
                "force_metadata_delete": force_metadata_delete,
            },
        )
    except Exception as exc:
        await target.reply_text(
            "❌ Не удалось удалить канал:\n"
            f"{_format_api_error(exc)}\n\n"
            "Если Telegram не даёт удалить канал, можно выбрать вариант «удалить только из базы». Это уберёт его из бота и автопостинга.",
            reply_markup=keyboard_for(user_id),
        )
        return

    title = data.get("title") or f"ID {channel_id}"
    mode = "в Telegram и базе проекта" if delete_in_telegram else "только из базы проекта"
    extra = ""
    if data.get("telegram_error"):
        extra = f"\n⚠️ Ошибка Telegram: {data.get('telegram_error')}"
    await target.reply_text(
        f"✅ Канал «{title}» удалён {mode}.{extra}",
        reply_markup=keyboard_for(user_id),
    )


async def delete_channel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_admin(update):
        return
    if context.args:
        try:
            channel_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Использование: /delete_channel <ID>", reply_markup=keyboard_for(update.effective_user.id))
            return
        await delete_channel_confirm(update, context, channel_id)
        return
    await delete_channel_menu(update, context)


def _status_panel_markup() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📢 Занятость каналов", callback_data="status_channels:0")],
            [InlineKeyboardButton("⏰ Автопостинг", callback_data="status_autoposting:0")],
            [InlineKeyboardButton("📋 Общий статус", callback_data="status_full:0")],
            [InlineKeyboardButton("🗑 Удалить канал", callback_data="delete_menu:0")],
        ]
    )


async def status_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await my_channel(update, context)
        return
    text = (
        "📊 Вкладка статусов\n\n"
        "Здесь собраны служебные проверки, чтобы не перегружать основное меню кнопками.\n"
        "Выберите, что посмотреть или удалить:"
    )
    target = update.callback_query.message if update.callback_query else update.message
    await target.reply_text(text, reply_markup=_status_panel_markup())


async def status_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await my_channel(update, context)
        return
    target = update.callback_query.message if update.callback_query else update.message
    try:
        channels_data = _api_get(f"{FULFILLMENT_URL}/api/get_all_channel?account_id={user_id}")
        channels = channels_data.get("items", [])
        free = sum(1 for ch in channels if not ch.get("is_booked"))
        busy = len(channels) - free
        by_type = {}
        for ch in channels:
            by_type[content_type_label(ch.get("content_type"))] = by_type.get(content_type_label(ch.get("content_type")), 0) + 1
        by_type_line = ", ".join(f"{k}: {v}" for k, v in by_type.items()) or "нет"
        text = (
            "📢 Занятость каналов\n"
            f"Всего: {len(channels)}\n"
            f"Свободно: {free}\n"
            f"Занято: {busy}\n"
            f"По типам: {by_type_line}\n\n"
            + _channel_lines(channels)
        )
        await target.reply_text(text, reply_markup=keyboard_for(user_id))
    except Exception as exc:
        await target.reply_text(f"❌ Не удалось получить статус каналов: {_format_api_error(exc)}", reply_markup=keyboard_for(user_id))


async def status_autoposting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await my_channel(update, context)
        return
    target = update.callback_query.message if update.callback_query else update.message
    try:
        scheduler_data = _api_get(f"{SCHEDULER_URL}/api/scheduler_status?account_id={user_id}")
        schedules = scheduler_data.get("schedules", [])
        jobs = scheduler_data.get("jobs", [])
        runs = scheduler_data.get("recent_runs", [])

        active_schedules = [s for s in schedules if s.get("active")]
        schedule_line = "нет активного расписания"
        if active_schedules:
            last = active_schedules[0]
            schedule_line = f"{last.get('cron')} ({last.get('timezone')})"

        next_run = "нет job в памяти"
        if jobs:
            next_run = jobs[0].get("next_run_time") or next_run

        last_run = "ещё не было"
        if runs:
            last_run = f"{runs[0].get('slot_key')} / {runs[0].get('source')}"

        await target.reply_text(
            "⏰ Автопостинг\n"
            f"Расписание: {schedule_line}\n"
            f"APScheduler работает: {scheduler_data.get('scheduler_running')}\n"
            f"Watchdog: {scheduler_data.get('watchdog_enabled')}\n"
            f"Следующий запуск: {next_run}\n"
            f"Последний hourly-slot: {last_run}\n\n"
            f"Готовое ежечасное расписание: /schedule {HOURLY_CRON}",
            reply_markup=keyboard_for(user_id),
        )
    except Exception as exc:
        await target.reply_text(f"❌ Не удалось получить статус автопостинга: {_format_api_error(exc)}", reply_markup=keyboard_for(user_id))


async def status_full(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await my_channel(update, context)
        return
    target = update.callback_query.message if update.callback_query else update.message
    try:
        channels_data = _api_get(f"{FULFILLMENT_URL}/api/get_all_channel?account_id={user_id}")
        channels = channels_data.get("items", [])
        free = sum(1 for ch in channels if not ch.get("is_booked"))
        busy = len(channels) - free
        by_type = {}
        for ch in channels:
            by_type[content_type_label(ch.get("content_type"))] = by_type.get(content_type_label(ch.get("content_type")), 0) + 1
        by_type_line = ", ".join(f"{k}: {v}" for k, v in by_type.items()) or "нет"

        scheduler_data = _api_get(f"{SCHEDULER_URL}/api/scheduler_status?account_id={user_id}")
        schedules = scheduler_data.get("schedules", [])
        jobs = scheduler_data.get("jobs", [])
        runs = scheduler_data.get("recent_runs", [])

        active_schedules = [s for s in schedules if s.get("active")]
        schedule_line = "нет активного расписания"
        if active_schedules:
            last = active_schedules[0]
            schedule_line = f"{last.get('cron')} ({last.get('timezone')})"

        next_run = "нет job в памяти"
        if jobs:
            next_run = jobs[0].get("next_run_time") or next_run

        last_run = "ещё не было"
        if runs:
            last_run = f"{runs[0].get('slot_key')} / {runs[0].get('source')}"

        await target.reply_text(
            "📊 Общий статус\n"
            f"Каналов всего: {len(channels)}\n"
            f"Свободно: {free}\n"
            f"Занято: {busy}\n"
            f"По типам: {by_type_line}\n\n"
            "⏰ Автопостинг\n"
            f"Расписание: {schedule_line}\n"
            f"APScheduler работает: {scheduler_data.get('scheduler_running')}\n"
            f"Watchdog: {scheduler_data.get('watchdog_enabled')}\n"
            f"Следующий запуск: {next_run}\n"
            f"Последний hourly-slot: {last_run}",
            reply_markup=keyboard_for(user_id),
        )
    except Exception as exc:
        await target.reply_text(f"❌ Не удалось получить статус: {_format_api_error(exc)}", reply_markup=keyboard_for(user_id))


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await status_panel(update, context)


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data or ""
    if data.startswith("create_type:"):
        if not is_admin(update.effective_user.id):
            await query.message.reply_text("⛔ Создавать каналы может только админ.", reply_markup=keyboard_for(update.effective_user.id))
            return
        content_type = data.split(":", 1)[1]
        if content_type not in CONTENT_TYPES:
            await query.message.reply_text("Некорректный тип канала.", reply_markup=keyboard_for(update.effective_user.id))
            return
        context.user_data["new_channel_content_type"] = content_type
        context.user_data["awaiting_channel_title"] = True
        await query.message.reply_text(
            f"Тип выбран: {content_type_label(content_type)}.\nТеперь введите название канала или /cancel для отмены:",
            reply_markup=keyboard_for(update.effective_user.id),
        )
        return

    try:
        action, raw_id = data.split(":", 1)
        item_id = int(raw_id)
    except ValueError:
        await query.message.reply_text("Некорректная кнопка.", reply_markup=keyboard_for(update.effective_user.id))
        return

    if action == "claim_channel":
        await get_channel(update, context)
    elif action == "confirm_joined":
        await confirm_joined(update, context)
    elif action == "status_channels":
        await status_channels(update, context)
    elif action == "status_autoposting":
        await status_autoposting(update, context)
    elif action == "status_full":
        await status_full(update, context)
    elif action == "delete_menu":
        await delete_channel_menu(update, context)
    elif action == "delete_channel":
        await delete_channel_confirm(update, context, item_id)
    elif action == "delete_channel_tg":
        await delete_channel_execute(update, context, item_id, delete_in_telegram=True, force_metadata_delete=False)
    elif action == "delete_channel_meta":
        await delete_channel_execute(update, context, item_id, delete_in_telegram=False, force_metadata_delete=True)
    elif action == "delete_cancel":
        await query.message.reply_text("Удаление отменено.", reply_markup=keyboard_for(update.effective_user.id))
    else:
        await query.message.reply_text("Неизвестное действие.", reply_markup=keyboard_for(update.effective_user.id))


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
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("cancel", cancel))

    app.add_handler(CommandHandler("get_channel", get_channel))
    app.add_handler(CommandHandler("confirm_joined", confirm_joined))
    app.add_handler(CommandHandler("my_channel", my_channel))
    app.add_handler(CommandHandler("available_channels", available_channels))

    app.add_handler(CommandHandler("create_channel", create_channel))
    app.add_handler(CommandHandler("list_channels", list_channels))
    app.add_handler(CommandHandler("schedule", schedule_command))
    app.add_handler(CommandHandler("publish_now", publish_now))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("delete_channel", delete_channel_command))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
