from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from tg_adapter_posting.services.telegram_client import send_telegram_message, edit_telegram_message

router = APIRouter()

class PostMessageRequest(BaseModel):
    channel_id: int
    access_hash: Optional[int] = None
    text: str
    parse_mode: str = "HTML"

class ChangeMessageRequest(BaseModel):
    new_text: str
    parse_mode: str = "HTML"
    channel_id: Optional[int] = None

@router.post("/api/post_msg/")
async def post_message(req: PostMessageRequest):
    try:
        msg_id = await send_telegram_message(req.channel_id, req.text, req.parse_mode, req.access_hash)
        return {"status": "sent", "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/change_msg/{msg_id}")
async def change_message(msg_id: int, req: ChangeMessageRequest):
    try:
        await edit_telegram_message(req.channel_id, msg_id, req.new_text, req.parse_mode)
        return {"status": "updated", "message_id": msg_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
