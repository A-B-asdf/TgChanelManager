from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from content_scheduler.core.database import delete_schedule, get_schedules_by_account, save_schedule_to_db
from content_scheduler.core.schemas import ScheduleSettings
from content_scheduler.services.scheduler_service import (
    ensure_hourly_schedule_for_account,
    publish_for_account,
    remove_scheduled_job,
    schedule_job,
    scheduler_status,
    validate_cron,
)

router = APIRouter()


@router.post("/api/add_account_schedule/{account_id}")
async def add_account_schedule(account_id: int, settings: ScheduleSettings):
    try:
        validate_cron(settings.cron, settings.timezone)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid cron or timezone: {exc}") from exc

    old_active_ids = [item["id"] for item in get_schedules_by_account(account_id) if item.get("active")]
    schedule_id = save_schedule_to_db(account_id, settings)
    for old_id in old_active_ids:
        remove_scheduled_job(old_id)

    if settings.active:
        schedule_job(schedule_id, account_id, settings.cron, settings.timezone)
    return {
        "status": "created",
        "account_id": account_id,
        "schedule_id": schedule_id,
        "cron": settings.cron,
        "timezone": settings.timezone,
        "active": settings.active,
        "replaced_schedule_ids": old_active_ids,
    }


@router.post("/api/ensure_hourly_schedule/{account_id}")
async def ensure_hourly_schedule(account_id: int):
    try:
        return ensure_hourly_schedule_for_account(account_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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


@router.get("/api/scheduler_status")
async def get_scheduler_status(account_id: Optional[int] = Query(default=None)):
    return scheduler_status(account_id=account_id)
