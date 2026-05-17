from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from fulfillment_service.core.database import (
    book_channel_db,
    create_channel_record,
    delete_channel_db,
    create_or_get_access_request_db,
    filter_channels_db,
    get_access_request_db,
    get_all_channels_db,
    get_assigned_channel_for_user_db,
    get_channel_by_id_db,
    list_access_requests_db,
    release_channel_db,
    reserve_next_available_channel_db,
    set_channel_invite_link_db,
    update_access_request_status_db,
    update_channel_handoff_db,
    update_channel_owner_db,
)
from fulfillment_service.services.channel_client import (
    call_channel_service_change_owner,
    call_channel_service_create,
    call_channel_service_create_invite_link,
    call_channel_service_delete,
    call_channel_service_finalize_transfer,
)
from fulfillment_service.services.scheduler_client import add_account_schedule

router = APIRouter()

CONTENT_TYPES = {"jokes", "news", "sport", "games", "recipes", "memes", "cats", "music"}


def normalize_content_type(value: Optional[str]) -> str:
    value = (value or "jokes").strip().lower()
    if value not in CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown content_type: {value}")
    return value


class FilterRequest(BaseModel):
    account_id: Optional[int] = None
    only_available: Optional[bool] = None
    content_type: Optional[str] = None
    topic: Optional[str] = None
    min_subscribers: Optional[int] = None
    language: Optional[str] = None


class CreateChannelRequest(BaseModel):
    title: str
    description: Optional[str] = None
    account_id: int
    content_type: str = "jokes"
    schedule_cron: Optional[str] = None


class BookChannelRequest(BaseModel):
    account_id: Optional[int] = None


class ChangeOwnerRequest(BaseModel):
    new_owner_id: int


class RequestAccessPayload(BaseModel):
    requester_account_id: int
    requester_username: Optional[str] = None
    requester_name: Optional[str] = None


class AdminAccessPayload(BaseModel):
    admin_account_id: Optional[int] = None
    requester_account_id: Optional[int] = None


class FinalizeClaimPayload(BaseModel):
    requester_account_id: int
    leave_after_admin: bool = True


class DeleteChannelRequest(BaseModel):
    account_id: Optional[int] = None
    delete_in_telegram: bool = True
    force_metadata_delete: bool = False


@router.get("/api/get_all_channel")
async def get_all_channels(account_id: Optional[int] = None, only_available: bool = False):
    return {"items": get_all_channels_db(account_id=account_id, only_available=only_available)}


@router.get("/api/get_available_channels")
async def get_available_channels():
    return {"items": get_all_channels_db(only_available=True)}


@router.get("/api/get_channel/{channel_id}")
async def get_channel(channel_id: int):
    ch = get_channel_by_id_db(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    return {"channel": ch}


@router.get("/api/my_channel/{account_id}")
async def my_channel(account_id: int):
    ch = get_assigned_channel_for_user_db(account_id)
    if not ch:
        raise HTTPException(status_code=404, detail="No channel assigned to this user")
    return {"channel": ch}


@router.post("/api/get_channel/filter")
async def filter_channels(payload: FilterRequest):
    filters = payload.dict(exclude_none=True)
    if filters.get("content_type"):
        filters["content_type"] = normalize_content_type(filters["content_type"])
    channels = filter_channels_db(filters)
    return {"items": channels}


@router.post("/api/book_channel/{channel_id}")
async def book_channel(channel_id: int, payload: Optional[BookChannelRequest] = None):
    owner_account_id = payload.account_id if payload else None
    success = book_channel_db(channel_id, owner_account_id=owner_account_id)
    if not success:
        raise HTTPException(status_code=400, detail="Channel already booked, not found, or does not belong to this account")
    return {"status": "booked", "reservation_id": f"res-{channel_id}"}


@router.post("/api/release_channel/{channel_id}")
async def release_channel(channel_id: int, payload: Optional[BookChannelRequest] = None):
    owner_account_id = payload.account_id if payload else None
    success = release_channel_db(channel_id, owner_account_id=owner_account_id)
    if not success:
        raise HTTPException(status_code=404, detail="Channel not found or does not belong to this admin")
    return {"status": "released", "channel_id": channel_id}


@router.post("/api/delete_channel/{channel_id}")
async def delete_channel(channel_id: int, payload: Optional[DeleteChannelRequest] = None):
    payload = payload or DeleteChannelRequest()
    ch = get_channel_by_id_db(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    if payload.account_id is not None and ch.get("owner_account_id") != payload.account_id:
        raise HTTPException(status_code=403, detail="This channel does not belong to this admin")

    telegram_result = None
    telegram_error = None
    if payload.delete_in_telegram:
        try:
            telegram_result = await call_channel_service_delete(
                ch["channel_id"],
                delete_in_telegram=True,
                force_metadata_delete=payload.force_metadata_delete,
            )
        except Exception as exc:
            telegram_error = str(exc)
            if not payload.force_metadata_delete:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Не удалось удалить канал в Telegram. "
                        "Если нужно убрать его только из базы проекта, используйте удаление только из базы. "
                        f"Техническая ошибка: {telegram_error}"
                    ),
                ) from exc
    else:
        try:
            telegram_result = await call_channel_service_delete(
                ch["channel_id"],
                delete_in_telegram=False,
                force_metadata_delete=True,
            )
        except Exception:
            # Даже если channel-service недоступен, fulfillment-метаданные можно удалить отдельно.
            telegram_result = None

    deleted = delete_channel_db(channel_id, owner_account_id=payload.account_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Channel not found or does not belong to this admin")
    return {
        "status": "deleted",
        "channel_id": channel_id,
        "channel_service_id": deleted.get("channel_id"),
        "title": deleted.get("title"),
        "content_type": deleted.get("content_type") or "jokes",
        "delete_in_telegram": payload.delete_in_telegram,
        "telegram": telegram_result,
        "telegram_error": telegram_error,
    }


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
    content_type = normalize_content_type(req.content_type)
    description = req.description or f"Тип контента: {content_type}"
    chan_resp = await call_channel_service_create(req.title, description, req.account_id)
    channel_service_id = chan_resp["channel_id"]
    tg_channel_id = chan_resp["tg_channel_id"]
    tg_access_hash = chan_resp.get("tg_access_hash")
    create_channel_record(channel_service_id, tg_channel_id, req.title, req.account_id, tg_access_hash, content_type)
    if req.schedule_cron:
        await add_account_schedule(req.account_id, req.schedule_cron)
    return {
        "channel_id": channel_service_id,
        "tg_channel_id": tg_channel_id,
        "tg_access_hash": tg_access_hash,
        "content_type": content_type,
        "status": "created",
    }


@router.post("/api/claim_available_channel")
async def claim_available_channel(payload: RequestAccessPayload):
    already = get_assigned_channel_for_user_db(payload.requester_account_id)
    if already:
        return {
            "status": "already_claimed",
            "channel_id": already["id"],
            "channel_title": already["title"],
            "content_type": already.get("content_type") or "jokes",
            "requester_account_id": payload.requester_account_id,
            "invite_link": already.get("invite_link"),
            "handoff_status": already.get("handoff_status"),
        }

    ch = reserve_next_available_channel_db(
        requester_account_id=payload.requester_account_id,
        requester_username=payload.requester_username,
        requester_name=payload.requester_name,
    )
    if not ch:
        raise HTTPException(status_code=404, detail="No free channels available")

    try:
        invite = await call_channel_service_create_invite_link(ch["channel_id"])
    except Exception as exc:
        release_channel_db(ch["id"])
        raise HTTPException(status_code=500, detail=f"Failed to create invite link: {exc}") from exc

    updated = set_channel_invite_link_db(ch["id"], invite["invite_link"])
    return {
        "status": "claimed",
        "channel_id": updated["id"],
        "channel_title": updated["title"],
        "content_type": updated.get("content_type") or "jokes",
        "requester_account_id": payload.requester_account_id,
        "invite_link": updated["invite_link"],
    }


@router.post("/api/finalize_channel_claim")
async def finalize_channel_claim(payload: FinalizeClaimPayload):
    ch = get_assigned_channel_for_user_db(payload.requester_account_id)
    if not ch:
        raise HTTPException(status_code=404, detail="No channel assigned to this user")

    if ch.get("handoff_status") == "completed" and ch.get("admin_left_at"):
        return {
            "status": "already_completed",
            "channel_id": ch["id"],
            "channel_title": ch["title"],
            "requester_account_id": payload.requester_account_id,
            "invite_link": ch.get("invite_link"),
            "handoff_status": ch.get("handoff_status"),
        }

    try:
        transfer = await call_channel_service_finalize_transfer(
            ch["channel_id"],
            requester_account_id=payload.requester_account_id,
            leave_after_admin=payload.leave_after_admin,
        )
    except Exception as exc:
        update_channel_handoff_db(ch["id"], "failed", error=str(exc)[:1000])
        raise HTTPException(
            status_code=400,
            detail=(
                "Не получилось завершить передачу. Сначала пользователь должен перейти по invite-ссылке в канал, "
                f"а потом нажать подтверждение. Техническая ошибка: {exc}"
            ),
        ) from exc

    admin_left = bool(transfer.get("admin_left"))
    promoted = bool(transfer.get("buyer_promoted"))
    if promoted and admin_left:
        status = "completed"
        error = None
    elif promoted:
        status = "promoted_admin_not_left"
        error = transfer.get("leave_error")
    else:
        status = "failed"
        error = transfer.get("error") or "Buyer was not promoted"

    updated = update_channel_handoff_db(
        ch["id"],
        status,
        buyer_promoted=promoted,
        admin_left=admin_left,
        error=error[:1000] if error else None,
    )
    return {
        "status": status,
        "channel_id": updated["id"],
        "channel_title": updated["title"],
        "content_type": updated.get("content_type") or "jokes",
        "requester_account_id": payload.requester_account_id,
        "invite_link": updated.get("invite_link"),
        "telegram": transfer,
        "handoff_status": updated.get("handoff_status"),
        "handoff_error": updated.get("handoff_error"),
    }


# Backward-compatible request/approval endpoints from the previous version.
@router.post("/api/request_access/{channel_id}")
async def request_access(channel_id: int, payload: RequestAccessPayload):
    ch = get_channel_by_id_db(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    if ch.get("owner_account_id") == payload.requester_account_id:
        raise HTTPException(status_code=400, detail="Owner already has access to this channel")

    request = create_or_get_access_request_db(
        channel_db_id=channel_id,
        requester_account_id=payload.requester_account_id,
        requester_username=payload.requester_username,
        requester_name=payload.requester_name,
    )
    status = request.get("status_alias") or request.get("status")
    return {
        "request_id": request["id"],
        "status": status,
        "channel_id": channel_id,
        "channel_title": request.get("channel_title"),
        "requester_account_id": payload.requester_account_id,
        "invite_link": request.get("invite_link"),
    }


@router.get("/api/access_requests")
async def access_requests(status: Optional[str] = None):
    return {"items": list_access_requests_db(status=status)}


@router.get("/api/my_access_requests/{requester_account_id}")
async def my_access_requests(requester_account_id: int):
    return {"items": list_access_requests_db(requester_account_id=requester_account_id)}


@router.post("/api/approve_access/{request_id}")
async def approve_access(request_id: int, payload: Optional[AdminAccessPayload] = None):
    request = get_access_request_db(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")
    if request["status"] == "approved" and request.get("invite_link"):
        return {
            "status": "approved",
            "request_id": request_id,
            "channel_id": request["channel_db_id"],
            "channel_title": request.get("channel_title"),
            "requester_account_id": request["requester_account_id"],
            "invite_link": request["invite_link"],
        }
    if request["status"] == "declined":
        raise HTTPException(status_code=400, detail="This request was declined")

    invite = await call_channel_service_create_invite_link(request["channel_id"])
    invite_link = invite["invite_link"]
    updated = update_access_request_status_db(request_id, "approved", invite_link=invite_link)
    book_channel_db(updated["channel_db_id"])
    return {
        "status": "approved",
        "request_id": request_id,
        "channel_id": updated["channel_db_id"],
        "channel_title": updated.get("channel_title"),
        "requester_account_id": updated["requester_account_id"],
        "invite_link": invite_link,
    }


@router.post("/api/decline_access/{request_id}")
async def decline_access(request_id: int, payload: Optional[AdminAccessPayload] = None):
    request = get_access_request_db(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Access request not found")
    if request["status"] == "approved":
        raise HTTPException(status_code=400, detail="Approved request cannot be declined")
    updated = update_access_request_status_db(request_id, "declined")
    return {
        "status": "declined",
        "request_id": request_id,
        "channel_id": updated["channel_db_id"],
        "channel_title": updated.get("channel_title"),
        "requester_account_id": updated["requester_account_id"],
    }


@router.post("/api/grant_access/{channel_id}")
async def grant_access(channel_id: int, payload: AdminAccessPayload):
    ch = get_channel_by_id_db(channel_id)
    if not ch:
        raise HTTPException(status_code=404, detail="Channel not found")
    if not payload.requester_account_id:
        raise HTTPException(status_code=400, detail="requester_account_id is required")
    invite = await call_channel_service_create_invite_link(ch["channel_id"])
    request = create_or_get_access_request_db(
        channel_db_id=channel_id,
        requester_account_id=payload.requester_account_id,
        requester_username=None,
        requester_name=None,
    )
    update_access_request_status_db(request["id"], "approved", invite_link=invite["invite_link"])
    return {
        "status": "approved",
        "channel_id": channel_id,
        "channel_title": ch["title"],
        "requester_account_id": payload.requester_account_id,
        "invite_link": invite["invite_link"],
    }
