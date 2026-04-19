from fastapi import APIRouter, HTTPException
from content_scheduler.core.schemas import ScheduleSettings
from content_scheduler.core.database import save_schedule_to_db, get_schedules_by_account, delete_schedule
from content_scheduler.services.scheduler_service import schedule_background_job
from typing import Dict

router = APIRouter()

@router.post("/api/add_account_schedule/{account_id}", response_model=Dict)
async def add_account_schedule(account_id: int, settings: ScheduleSettings):
    schedule_id = save_schedule_to_db(account_id, settings)
    if settings.active:
        schedule_background_job(schedule_id, settings.cron, settings.timezone, account_id)
    return {
        "status": "created",
        "account_id": account_id,
        "schedule_id": schedule_id,
        "cron": settings.cron,
        "active": settings.active
    }

@router.get("/api/schedules/{account_id}")
async def get_schedules(account_id: int):
    return get_schedules_by_account(account_id)

@router.delete("/api/schedule/{schedule_id}")
async def remove_schedule(schedule_id: int):
    if delete_schedule(schedule_id):
        return {"status": "deleted", "schedule_id": schedule_id}
    raise HTTPException(status_code=404, detail="Schedule not found")