from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, Optional
import uvicorn

app = FastAPI(
    title="TgAdapterPosting Service",
    description="Stub adapter service for Telegram posting operations",
    version="0.1.0",
)


class PostMessageRequest(BaseModel):
    channel_id: int
    text: str
    parse_mode: Optional[str] = "HTML"


class ChangeMessageRequest(BaseModel):
    new_text: str
    channel_id: Optional[int] = None
    parse_mode: Optional[str] = "HTML"


@app.post("/api/post_msg/")
async def post_message(payload: PostMessageRequest) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "post_msg",
        "message_id": 9001,
        "payload": payload.model_dump(),
    }


@app.post("/api/change_msg/{msg_id}")
async def change_message(msg_id: int, payload: ChangeMessageRequest) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "change_msg",
        "message_id": msg_id,
        "payload": payload.model_dump(),
    }


@app.get("/api/get_channel_info")
async def get_channel_info() -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "get_channel_info",
        "channel": {
            "channel_id": 1,
            "name": "demo-channel",
            "created_at": "2026-01-01T00:00:00Z",
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8005)
