from fastapi import APIRouter, HTTPException

from content_scheduler.core.database import delete_schedule, get_schedules_by_account, save_schedule_to_db
from content_scheduler.core.schemas import ScheduleSettings
from content_scheduler.services.scheduler_service import (
    publish_for_account,
    remove_scheduled_job,
    schedule_job,
    validate_cron,
)

router = APIRouter()


@router.post("/api/add_account_schedule/{account_id}")
async def add_account_schedule(account_id: int, settings: ScheduleSettings):
    try:
        validate_cron(settings.cron, settings.timezone)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid cron or timezone: {exc}") from exc

    schedule_id = save_schedule_to_db(account_id, settings)
    if settings.active:
        schedule_job(schedule_id, account_id, settings.cron, settings.timezone)
    return {
        "status": "created",
        "account_id": account_id,
        "schedule_id": schedule_id,
        "cron": settings.cron,
        "timezone": settings.timezone,
        "active": settings.active,
    }


@router.get("/api/schedules/{account_id}")
async def get_schedules(account_id: int):
    return {"items": get_schedules_by_account(account_id)}


@router.delete("/api/schedule/{schedule_id}")
async def remove_schedule(schedule_id: int):
    removed_from_scheduler = remove_scheduled_job(schedule_id)
    if delete_schedule(schedule_id):
        return {
            "status": "deleted",
            "schedule_id": schedule_id,
            "removed_from_scheduler": removed_from_scheduler,
        }
    raise HTTPException(status_code=404, detail="Schedule not found")


@router.post("/api/publish_now/{account_id}")
async def publish_now(account_id: int):
    return publish_for_account(account_id)
