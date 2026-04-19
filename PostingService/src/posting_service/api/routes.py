from fastapi import APIRouter, HTTPException
from posting_service.core.schemas import PostMessageRequest, ChangeMessageRequest
from posting_service.services.message_service import send_message, edit_message
from posting_service.core.database import get_message_logs

router = APIRouter()

@router.post("/api/post_msg/")
async def post_message(request: PostMessageRequest):
    result = send_message(request.channel_id, request.text, request.parse_mode or "HTML")
    return result

@router.post("/api/change_msg/{msg_id}")
async def change_message(msg_id: int, request: ChangeMessageRequest):
    result = edit_message(msg_id, request.new_text, request.parse_mode or "HTML", request.channel_id)
    return result

@router.get("/api/logs")
async def logs(limit: int = 100):
    return get_message_logs(limit)