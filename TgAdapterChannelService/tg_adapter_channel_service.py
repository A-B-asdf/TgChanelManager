from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, Optional
import uvicorn

app = FastAPI(
    title="TgAdapterChannel Service",
    description="Stub adapter service for Telegram channel operations",
    version="0.1.0",
)


class CreateTgChannelRequest(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    language: Optional[str] = None


class ChangeOwnerRequest(BaseModel):
    owner_id: Optional[int] = None


@app.post("/api/create_tg_channel")
async def create_tg_channel(payload: CreateTgChannelRequest) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "create_tg_channel",
        "tg_channel_id": 101,
        "payload": payload.model_dump(),
    }


@app.get("/api/get_tg_channel_info")
async def get_tg_channel_info() -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "get_tg_channel_info",
        "channel": {
            "tg_channel_id": 101,
            "name": "demo-tg-channel",
            "created_at": "2026-01-01T00:00:00Z",
        },
    }


@app.get("/api/get_tg_channel_statistic")
async def get_tg_channel_statistic() -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "get_tg_channel_statistic",
        "statistics": {
            "subscribers": 1234,
            "posts_count": 56,
            "engagement_rate": 0.12,
        },
    }


@app.post("/api/change_owner/{channel_id}")
async def change_owner(channel_id: int, payload: ChangeOwnerRequest) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "change_owner",
        "channel_id": channel_id,
        "payload": payload.model_dump(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8004)
