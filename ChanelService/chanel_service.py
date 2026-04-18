from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, Optional
import uvicorn

app = FastAPI(
    title="Channel Service",
    description="Stub service for channel lifecycle and ownership operations",
    version="0.1.0",
)


class CreateChannelRequest(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    language: Optional[str] = None


class ChangeOwnerRequest(BaseModel):
    owner_id: Optional[int] = None


@app.post("/api/create_channel")
async def create_channel(payload: CreateChannelRequest) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "create_channel",
        "channel_id": 1,
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


@app.post("/api/change_owner/{channel_id}")
async def change_owner(channel_id: int, payload: ChangeOwnerRequest) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "change_owner",
        "channel_id": channel_id,
        "payload": payload.model_dump(),
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
