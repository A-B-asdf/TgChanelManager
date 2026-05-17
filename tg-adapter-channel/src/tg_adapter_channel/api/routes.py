from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from tg_adapter_channel.services.telegram_channel import (
    change_channel_owner,
    create_channel_invite_link,
    create_telegram_channel,
    delete_telegram_channel,
    finalize_channel_transfer,
    get_channel_info,
    get_channel_statistic,
    leave_telegram_channel,
)

router = APIRouter()


class CreateChannelRequest(BaseModel):
    title: str
    about: Optional[str] = None


class ChangeOwnerRequest(BaseModel):
    new_owner_id: int


class InviteLinkRequest(BaseModel):
    channel_id: int
    access_hash: Optional[int] = None


class FinalizeChannelTransferRequest(BaseModel):
    channel_id: int
    access_hash: Optional[int] = None
    requester_account_id: int
    leave_after_admin: bool = True


@router.post("/api/create_tg_channel")
async def create_channel(req: CreateChannelRequest):
    try:
        channel = await create_telegram_channel(req.title, req.about)
        return {"status": "created", **channel}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/create_invite_link")
async def create_invite_link(req: InviteLinkRequest):
    try:
        invite = await create_channel_invite_link(req.channel_id, req.access_hash)
        return {"status": "created", **invite}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/delete_channel")
async def delete_channel(req: InviteLinkRequest):
    try:
        result = await delete_telegram_channel(req.channel_id, req.access_hash)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/leave_channel")
async def leave_channel(req: InviteLinkRequest):
    try:
        result = await leave_telegram_channel(req.channel_id, req.access_hash)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/finalize_channel_transfer")
async def finalize_transfer(req: FinalizeChannelTransferRequest):
    try:
        return await finalize_channel_transfer(
            channel_id=req.channel_id,
            access_hash=req.access_hash,
            requester_account_id=req.requester_account_id,
            leave_after_admin=req.leave_after_admin,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


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
