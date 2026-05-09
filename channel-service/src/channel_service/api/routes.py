from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from channel_service.core.database import create_channel_record, get_channel_info_from_db, update_channel_owner
from channel_service.services.tg_adapter import create_telegram_channel, change_telegram_owner

router = APIRouter()

class CreateChannelRequest(BaseModel):
    title: str
    description: Optional[str] = None
    account_id: int

class ChangeOwnerRequest(BaseModel):
    new_owner_id: int

@router.post("/api/create_channel")
async def create_channel(req: CreateChannelRequest):
    tg_channel = await create_telegram_channel(req.title, req.description)
    tg_channel_id = tg_channel["tg_channel_id"]
    tg_access_hash = tg_channel.get("tg_access_hash")
    channel_id = create_channel_record(tg_channel_id, req.title, req.account_id, tg_access_hash)
    return {
        "channel_id": channel_id,
        "tg_channel_id": tg_channel_id,
        "tg_access_hash": tg_access_hash,
        "status": "created",
    }

@router.get("/api/get_channel_info/{channel_id}")
async def get_channel_info(channel_id: int):
    info = get_channel_info_from_db(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail="Channel not found")
    return info

@router.post("/api/change_owner/{channel_id}")
async def change_owner(channel_id: int, req: ChangeOwnerRequest):
    info = get_channel_info_from_db(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail="Channel not found")
    await change_telegram_owner(info["tg_channel_id"], req.new_owner_id)
    update_channel_owner(channel_id, req.new_owner_id)
    return {"status": "owner_updated", "channel_id": channel_id, "new_owner_id": req.new_owner_id}
