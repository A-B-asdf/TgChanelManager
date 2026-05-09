from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from fulfillment_service.core.database import (
    book_channel_db,
    create_channel_record,
    filter_channels_db,
    get_all_channels_db,
    get_channel_by_id_db,
    update_channel_owner_db,
)
from fulfillment_service.services.channel_client import call_channel_service_change_owner, call_channel_service_create
from fulfillment_service.services.scheduler_client import add_account_schedule

router = APIRouter()


class FilterRequest(BaseModel):
    account_id: Optional[int] = None
    topic: Optional[str] = None
    min_subscribers: Optional[int] = None
    language: Optional[str] = None


class CreateChannelRequest(BaseModel):
    title: str
    description: Optional[str] = None
    account_id: int
    schedule_cron: Optional[str] = None


class BookChannelRequest(BaseModel):
    account_id: Optional[int] = None


class ChangeOwnerRequest(BaseModel):
    new_owner_id: int


@router.get("/api/get_all_channel")
async def get_all_channels(account_id: Optional[int] = None):
    return {"items": get_all_channels_db(account_id=account_id)}


@router.get("/api/get_channel/{channel_id}")
async def get_channel(channel_id: int):
    ch = get_channel_by_id_db(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"channel": ch}


@router.post("/api/get_channel/filter")
async def filter_channels(payload: FilterRequest):
    channels = filter_channels_db(payload.dict(exclude_none=True))
    return {"items": channels}


@router.post("/api/book_channel/{channel_id}")
async def book_channel(channel_id: int, payload: Optional[BookChannelRequest] = None):
    owner_account_id = payload.account_id if payload else None
    success = book_channel_db(channel_id, owner_account_id=owner_account_id)
    if not success:
        raise HTTPException(status_code=400, detail="Channel already booked, not found, or does not belong to this account")
    return {"status": "booked", "reservation_id": f"res-{channel_id}"}


@router.post("/api/change_owner/{channel_id}")
async def change_owner(channel_id: int, payload: ChangeOwnerRequest):
    ch = get_channel_by_id_db(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    await call_channel_service_change_owner(ch["channel_id"], payload.new_owner_id)
    update_channel_owner_db(channel_id, payload.new_owner_id)
    return {"status": "owner_change_initiated", "channel_id": channel_id, "new_owner_id": payload.new_owner_id}


@router.post("/api/create_channel")
async def create_channel(req: CreateChannelRequest):
    chan_resp = await call_channel_service_create(req.title, req.description or "", req.account_id)
    channel_service_id = chan_resp["channel_id"]
    tg_channel_id = chan_resp["tg_channel_id"]
    tg_access_hash = chan_resp.get("tg_access_hash")
    create_channel_record(channel_service_id, tg_channel_id, req.title, req.account_id, tg_access_hash)
    if req.schedule_cron:
        await add_account_schedule(req.account_id, req.schedule_cron)
    return {
        "channel_id": channel_service_id,
        "tg_channel_id": tg_channel_id,
        "tg_access_hash": tg_access_hash,
        "status": "created",
    }
