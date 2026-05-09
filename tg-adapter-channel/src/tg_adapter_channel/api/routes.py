from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from tg_adapter_channel.services.telegram_channel import create_telegram_channel, change_channel_owner, get_channel_info, get_channel_statistic

router = APIRouter()

class CreateChannelRequest(BaseModel):
    title: str
    about: Optional[str] = None

class ChangeOwnerRequest(BaseModel):
    new_owner_id: int

@router.post("/api/create_tg_channel")
async def create_channel(req: CreateChannelRequest):
    try:
        channel = await create_telegram_channel(req.title, req.about)
        return {"status": "created", **channel}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/change_owner/{channel_id}")
async def change_owner(channel_id: int, req: ChangeOwnerRequest):
    try:
        await change_channel_owner(channel_id, req.new_owner_id)
        return {"status": "owner_changed", "channel_id": channel_id, "new_owner_id": req.new_owner_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/get_tg_channel_info/{channel_id}")
async def get_info(channel_id: int):
    try:
        info = await get_channel_info(channel_id)
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/get_tg_channel_statistic/{channel_id}")
async def get_statistic(channel_id: int):
    try:
        stats = await get_channel_statistic(channel_id)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
