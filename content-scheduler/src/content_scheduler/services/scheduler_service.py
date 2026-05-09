import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from content_scheduler.core.database import get_active_schedules
from content_scheduler.services.anekdot_parser import fetch_anekdot
from content_scheduler.services.channel_client import get_channels_by_account
from content_scheduler.services.posting_client import send_to_posting_service

scheduler = BackgroundScheduler()
scheduler.start()
logger = logging.getLogger(__name__)


def validate_cron(cron: str, timezone: str) -> None:
    CronTrigger.from_crontab(cron, timezone=timezone)


def schedule_job(schedule_id: int, account_id: int, cron: str, timezone: str):
    trigger = CronTrigger.from_crontab(cron, timezone=timezone)
    scheduler.add_job(
        func=publish_for_account,
        trigger=trigger,
        args=[account_id],
        id=f"job_{schedule_id}",
        replace_existing=True,
    )
    logger.info("Scheduled job %s for account %s with cron %s", schedule_id, account_id, cron)


def remove_scheduled_job(schedule_id: int) -> bool:
    job_id = f"job_{schedule_id}"
    job = scheduler.get_job(job_id)
    if not job:
        return False
    scheduler.remove_job(job_id)
    logger.info("Removed job %s", job_id)
    return True


def restore_active_schedules() -> int:
    restored = 0
    for item in get_active_schedules():
        try:
            schedule_job(
                schedule_id=item["id"],
                account_id=item["account_id"],
                cron=item["cron"],
                timezone=item["timezone"],
            )
            restored += 1
        except Exception as exc:
            logger.exception("Failed to restore schedule %s: %s", item.get("id"), exc)
    return restored


def publish_for_account(account_id: int) -> dict:
    logger.info("Publishing for account %s", account_id)
    channels = get_channels_by_account(account_id)
    if not channels:
        logger.warning("No channels found for account %s", account_id)
        return {"status": "no_channels", "account_id": account_id, "sent": 0, "failed": 0, "errors": ["У аккаунта нет каналов с tg_channel_id"]}

    try:
        text = fetch_anekdot()
    except Exception as exc:
        logger.exception("Failed to fetch content for account %s: %s", account_id, exc)
        return {"status": "content_error", "account_id": account_id, "sent": 0, "failed": len(channels), "errors": [f"Не удалось загрузить анекдот: {exc}"]}

    sent = 0
    errors = []
    results = []
    for ch in channels:
        ch_id = ch["channel_id"]
        try:
            result = send_to_posting_service(ch_id, text, ch.get("access_hash"))
            logger.info("Sent to Telegram channel %s: %s", ch_id, result)
            sent += 1
            results.append(result)
        except Exception as exc:
            logger.exception("Failed to send to Telegram channel %s: %s", ch_id, exc)
            errors.append(f"{ch.get('title') or ch_id}: {exc}")

    return {
        "status": "done" if not errors else "partial_failed",
        "account_id": account_id,
        "sent": sent,
        "failed": len(errors),
        "errors": errors,
        "results": results,
    }
