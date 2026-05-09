from fastapi import APIRouter, HTTPException

from posting_service.core.schemas import ChangeMessageRequest, PostMessageRequest
from posting_service.services.message_service import edit_message, send_message

router = APIRouter()


@router.post("/api/post_msg/")
async def post_message(request: PostMessageRequest):
    try:
        return send_message(request.channel_id, request.text, request.parse_mode or "HTML", request.access_hash)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/api/change_msg/{msg_id}")
async def change_message(msg_id: int, request: ChangeMessageRequest):
    if request.channel_id is None:
        raise HTTPException(status_code=400, detail="channel_id is required to edit a Telegram message")
    try:
        return edit_message(msg_id, request.new_text, request.parse_mode or "HTML", request.channel_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/api/logs")
async def get_logs(limit: int = 100):
    from posting_service.core.database import get_message_logs

    return {"items": get_message_logs(limit)}
