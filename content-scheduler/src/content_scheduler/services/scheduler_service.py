import logging
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from content_scheduler.core.config import Config
from content_scheduler.core.database import (
    content_hash,
    ensure_active_schedule,
    get_active_schedules,
    get_recent_content_hashes,
    get_recent_scheduled_runs,
    get_schedule_by_id,
    get_schedules_by_account,
    mark_scheduled_run,
    save_published_content,
)
from content_scheduler.services.content_sources import content_type_label, fetch_content_items, normalize_content_type
from content_scheduler.services.channel_client import get_channels_by_account
from content_scheduler.services.posting_client import send_to_posting_service

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone=Config.DEFAULT_TIMEZONE)
_watchdog_started = False
_watchdog_lock = threading.Lock()


def _safe_timezone(timezone: Optional[str]) -> ZoneInfo:
    try:
        return ZoneInfo(timezone or Config.DEFAULT_TIMEZONE)
    except ZoneInfoNotFoundError:
        logger.warning("Unknown timezone %s, using %s", timezone, Config.DEFAULT_TIMEZONE)
        return ZoneInfo(Config.DEFAULT_TIMEZONE)


def _hour_slot_key(timezone: Optional[str]) -> str:
    now = datetime.now(_safe_timezone(timezone))
    return f"hourly:{now.strftime('%Y-%m-%dT%H')}"


def _is_hourly_cron(cron: str) -> bool:
    parts = cron.split()
    return len(parts) == 5 and parts[0] == "0" and parts[1] in {"*", "*/1"}


def validate_cron(cron: str, timezone: str) -> None:
    CronTrigger.from_crontab(cron, timezone=timezone)


def _ensure_scheduler_started() -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started with default timezone %s", Config.DEFAULT_TIMEZONE)


def schedule_job(schedule_id: int, account_id: int, cron: str, timezone: str):
    _ensure_scheduler_started()
    trigger = CronTrigger.from_crontab(cron, timezone=timezone)
    scheduler.add_job(
        func=publish_scheduled,
        trigger=trigger,
        args=[schedule_id, account_id, timezone],
        id=f"job_{schedule_id}",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=3600,
    )
    job = scheduler.get_job(f"job_{schedule_id}")
    logger.info(
        "Scheduled job_%s for account %s with cron %s timezone %s next_run=%s",
        schedule_id,
        account_id,
        cron,
        timezone,
        job.next_run_time if job else None,
    )


def remove_scheduled_job(schedule_id: int) -> bool:
    job_id = f"job_{schedule_id}"
    job = scheduler.get_job(job_id)
    if not job:
        return False
    scheduler.remove_job(job_id)
    logger.info("Removed job %s", job_id)
    return True


def _item_signature(item: Dict) -> str:
    return str(item.get("text") or "") + "\n" + str(item.get("media_url") or "")


def _pick_fresh_content(account_id: int, content_type: str) -> Dict:
    recent_hashes = get_recent_content_hashes(account_id)
    candidates = fetch_content_items(content_type, limit=30)
    for item in candidates:
        if content_hash(_item_signature(item)) not in recent_hashes:
            return item
    return candidates[0]


def publish_for_account(account_id: int) -> Dict:
    logger.info("Publishing for account %s", account_id)
    channels = get_channels_by_account(account_id)
    if not channels:
        logger.warning("No channels found for account %s", account_id)
        return {
            "status": "no_channels",
            "account_id": account_id,
            "sent": 0,
            "failed": 0,
            "errors": ["У аккаунта нет свободных каналов с tg_channel_id"],
        }

    sent = 0
    errors: List[str] = []
    results = []
    content_cache: Dict[str, Dict] = {}

    for ch in channels:
        ch_id = ch["channel_id"]
        content_type = normalize_content_type(ch.get("content_type"))
        label = content_type_label(content_type)
        try:
            if content_type not in content_cache:
                content_cache[content_type] = _pick_fresh_content(account_id, content_type)
            item = content_cache[content_type]
            text = str(item.get("text") or "")
            media_url = item.get("media_url")
        except Exception as exc:
            logger.exception("Failed to fetch %s content for account %s: %s", content_type, account_id, exc)
            errors.append(f"{ch.get('title') or ch_id} [{label}]: не удалось загрузить контент: {exc}")
            continue

        try:
            result = send_to_posting_service(ch_id, text, ch.get("access_hash"), media_url=media_url)
            logger.info("Sent %s content to Telegram channel %s: %s", content_type, ch_id, result)
            sent += 1
            save_published_content(account_id, _item_signature(item))
            results.append({"channel_title": ch.get("title"), "content_type": content_type, "content_type_label": label, "has_media": bool(media_url), "telegram": result})
        except Exception as exc:
            logger.exception("Failed to send to Telegram channel %s: %s", ch_id, exc)
            errors.append(f"{ch.get('title') or ch_id} [{label}]: {exc}")

    return {
        "status": "done" if not errors else "partial_failed",
        "account_id": account_id,
        "sent": sent,
        "failed": len(errors),
        "errors": errors,
        "results": results,
    }


def publish_scheduled(schedule_id: int, account_id: int, timezone: str, source: str = "apscheduler") -> Dict:
    """Publish once per account per hour. DB lock prevents duplicate posts."""
    slot_key = _hour_slot_key(timezone)
    if not mark_scheduled_run(account_id, schedule_id, slot_key, source):
        logger.info("Skip duplicate scheduled run account=%s schedule=%s slot=%s source=%s", account_id, schedule_id, slot_key, source)
        return {"status": "duplicate_skipped", "account_id": account_id, "schedule_id": schedule_id, "slot_key": slot_key}
    logger.info("Run scheduled publish account=%s schedule=%s slot=%s source=%s", account_id, schedule_id, slot_key, source)
    return publish_for_account(account_id)


def _watchdog_tick() -> None:
    schedules = get_active_schedules()
    for item in schedules:
        cron = str(item.get("cron") or "")
        if not _is_hourly_cron(cron):
            continue
        timezone = item.get("timezone") or Config.DEFAULT_TIMEZONE
        now = datetime.now(_safe_timezone(timezone))
        if now.minute != 0:
            continue
        try:
            publish_scheduled(
                schedule_id=int(item["id"]),
                account_id=int(item["account_id"]),
                timezone=timezone,
                source="watchdog",
            )
        except Exception as exc:
            logger.exception("Watchdog publish failed for schedule %s: %s", item.get("id"), exc)


def _watchdog_loop() -> None:
    logger.info("Scheduler watchdog started")
    while True:
        try:
            _watchdog_tick()
        except Exception as exc:
            logger.exception("Scheduler watchdog tick failed: %s", exc)
        time.sleep(30)


def start_watchdog_once() -> None:
    global _watchdog_started
    if not Config.SCHEDULE_WATCHDOG_ENABLED:
        logger.info("Scheduler watchdog disabled")
        return
    with _watchdog_lock:
        if _watchdog_started:
            return
        thread = threading.Thread(target=_watchdog_loop, name="scheduler-watchdog", daemon=True)
        thread.start()
        _watchdog_started = True


def ensure_admin_hourly_schedules() -> List[int]:
    created_or_existing: List[int] = []
    if not Config.AUTO_CREATE_ADMIN_SCHEDULES:
        return created_or_existing
    for account_id in Config.ADMIN_USER_IDS:
        schedule_id = ensure_active_schedule(account_id, Config.HOURLY_CRON, Config.DEFAULT_TIMEZONE)
        created_or_existing.append(schedule_id)
        logger.info("Ensured hourly schedule for admin account %s: schedule_id=%s", account_id, schedule_id)
    return created_or_existing



def ensure_hourly_schedule_for_account(account_id: int) -> Dict:
    schedule_id = ensure_active_schedule(account_id, Config.HOURLY_CRON, Config.DEFAULT_TIMEZONE)
    item = get_schedule_by_id(schedule_id)
    if not item:
        raise RuntimeError(f"Schedule {schedule_id} was not found after creation")
    schedule_job(
        schedule_id=int(item["id"]),
        account_id=int(item["account_id"]),
        cron=str(item["cron"]),
        timezone=str(item["timezone"]),
    )
    return {
        "status": "ensured",
        "account_id": account_id,
        "schedule_id": schedule_id,
        "cron": item["cron"],
        "timezone": item["timezone"],
        "active": item["active"],
    }

def restore_active_schedules() -> int:
    _ensure_scheduler_started()
    ensure_admin_hourly_schedules()

    restored = 0
    accounts_to_publish = set()
    for item in get_active_schedules():
        try:
            schedule_job(
                schedule_id=int(item["id"]),
                account_id=int(item["account_id"]),
                cron=str(item["cron"]),
                timezone=str(item["timezone"]),
            )
            accounts_to_publish.add(int(item["account_id"]))
            restored += 1
        except Exception as exc:
            logger.exception("Failed to restore schedule %s: %s", item.get("id"), exc)

    start_watchdog_once()

    if Config.PUBLISH_ON_STARTUP:
        for account_id in accounts_to_publish:
            try:
                logger.info("Startup publish for account %s", account_id)
                publish_for_account(account_id)
            except Exception as exc:
                logger.exception("Startup publish failed for account %s: %s", account_id, exc)
    return restored


def scheduler_status(account_id: Optional[int] = None) -> Dict:
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "next_run_time": str(job.next_run_time) if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
        )
    schedules = get_schedules_by_account(account_id) if account_id is not None else get_active_schedules()
    return {
        "scheduler_running": scheduler.running,
        "default_timezone": Config.DEFAULT_TIMEZONE,
        "hourly_cron": Config.HOURLY_CRON,
        "admin_user_ids_configured": bool(Config.ADMIN_USER_IDS),
        "auto_create_admin_schedules": Config.AUTO_CREATE_ADMIN_SCHEDULES,
        "publish_on_startup": Config.PUBLISH_ON_STARTUP,
        "watchdog_enabled": Config.SCHEDULE_WATCHDOG_ENABLED,
        "jobs": jobs,
        "schedules": schedules,
        "recent_runs": get_recent_scheduled_runs(account_id=account_id, limit=10),
    }
