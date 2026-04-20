from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from content_scheduler.services.anekdot_parser import fetch_anekdot
from content_scheduler.services.posting_client import send_to_posting_service
from content_scheduler.core.database import get_schedules_by_account  # можно расширить
import logging

scheduler = BackgroundScheduler()
scheduler.start()


def schedule_background_job(schedule_id: int, cron: str, timezone: str, account_id: int):
    trigger = CronTrigger.from_crontab(cron, timezone=timezone)
    scheduler.add_job(
        func=publish_for_account,
        trigger=trigger,
        args=[account_id],
        id=f"job_{schedule_id}",
        replace_existing=True
    )


def get_channels_for_account(account_id: int) -> list[int]:
    """
    Stub-источник каналов для аккаунта.
    В будущем здесь должен быть вызов Channel/Fulfillment сервиса по account_id.
    """
    logging.info("Using stub channel source for account_id=%s", account_id)
    return [123, 456]


def publish_for_account(account_id: int):
    channels = get_channels_for_account(account_id)
    text = fetch_anekdot()
    for ch_id in channels:
        send_to_posting_service(ch_id, text)