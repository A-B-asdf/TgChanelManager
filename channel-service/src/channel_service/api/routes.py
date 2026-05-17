from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from channel_service.core.database import create_channel_record, delete_channel_record, get_channel_info_from_db, update_channel_owner
from channel_service.services.tg_adapter import (
    change_telegram_owner,
    create_telegram_channel,
    delete_telegram_channel,
    create_telegram_invite_link,
    finalize_telegram_transfer,
    leave_telegram_channel,
)

router = APIRouter()


class CreateChannelRequest(BaseModel):
    title: str
    description: Optional[str] = None
    account_id: int


class ChangeOwnerRequest(BaseModel):
    new_owner_id: int


class FinalizeTransferRequest(BaseModel):
    requester_account_id: int
    leave_after_admin: bool = True


class DeleteChannelRequest(BaseModel):
    delete_in_telegram: bool = True
    force_metadata_delete: bool = False


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


@router.post("/api/delete_channel/{channel_id}")
async def delete_channel(channel_id: int, req: DeleteChannelRequest):
    info = get_channel_info_from_db(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail="Channel not found")

    telegram_result = None
    telegram_error = None
    if req.delete_in_telegram:
        try:
            telegram_result = await delete_telegram_channel(info["tg_channel_id"], info.get("tg_access_hash"))
        except Exception as exc:
            telegram_error = str(exc)
            if not req.force_metadata_delete:
                raise HTTPException(status_code=500, detail=f"Telegram delete failed: {telegram_error}") from exc

    delete_channel_record(channel_id)
    return {
        "status": "deleted",
        "channel_id": channel_id,
        "tg_channel_id": info.get("tg_channel_id"),
        "title": info.get("title"),
        "delete_in_telegram": req.delete_in_telegram,
        "telegram": telegram_result,
        "telegram_error": telegram_error,
    }


@router.get("/api/get_channel_info/{channel_id}")
async def get_channel_info(channel_id: int):
    info = get_channel_info_from_db(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail="Channel not found")
    return info


@router.post("/api/create_invite_link/{channel_id}")
async def create_invite_link(channel_id: int):
    info = get_channel_info_from_db(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail="Channel not found")
    result = await create_telegram_invite_link(info["tg_channel_id"], info.get("tg_access_hash"))
    return {"status": "created", "channel_id": channel_id, **result}


@router.post("/api/leave_channel/{channel_id}")
async def leave_channel(channel_id: int):
    info = get_channel_info_from_db(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail="Channel not found")
    result = await leave_telegram_channel(info["tg_channel_id"], info.get("tg_access_hash"))
    return {"status": "left", "channel_id": channel_id, "telegram": result}


@router.post("/api/finalize_transfer/{channel_id}")
async def finalize_transfer(channel_id: int, req: FinalizeTransferRequest):
    info = get_channel_info_from_db(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail="Channel not found")
    try:
        result = await finalize_telegram_transfer(
            tg_channel_id=info["tg_channel_id"],
            tg_access_hash=info.get("tg_access_hash"),
            requester_account_id=req.requester_account_id,
            leave_after_admin=req.leave_after_admin,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "finalized", "channel_id": channel_id, "telegram": result, **result}


@router.post("/api/change_owner/{channel_id}")
async def change_owner(channel_id: int, req: ChangeOwnerRequest):
    info = get_channel_info_from_db(channel_id)
    if not info:
        raise HTTPException(status_code=404, detail="Channel not found")
    await change_telegram_owner(info["tg_channel_id"], req.new_owner_id)
    update_channel_owner(channel_id, req.new_owner_id)
    return {"status": "owner_updated", "channel_id": channel_id, "new_owner_id": req.new_owner_id}
