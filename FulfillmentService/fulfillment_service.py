from fastapi import FastAPI
from pydantic import BaseModel
from typing import Any, Dict, Optional
import uvicorn

app = FastAPI(
    title="Fulfillment Service",
    description="Stub service for order fulfillment orchestration",
    version="0.1.0",
)


class FilterChannelsRequest(BaseModel):
    topic: Optional[str] = None
    min_subscribers: Optional[int] = None
    language: Optional[str] = None


class CreateChannelRequest(BaseModel):
    title: Optional[str] = None
    topic: Optional[str] = None
    language: Optional[str] = None
    account_id: Optional[int] = None


@app.get("/api/get_all_channel")
async def get_all_channels() -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "get_all_channel",
        "items": [
            {"channel_id": 1, "name": "demo-channel-1"},
            {"channel_id": 2, "name": "demo-channel-2"},
        ],
    }


@app.get("/api/get_channel/{channel_id}")
async def get_channel(channel_id: int) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "get_channel",
        "channel": {"channel_id": channel_id, "name": f"demo-channel-{channel_id}"},
    }


@app.post("/api/get_channel/filter")
async def filter_channels(payload: FilterChannelsRequest) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "filter_channels",
        "criteria": payload.model_dump(),
        "items": [{"channel_id": 1, "name": "demo-channel-1"}],
    }


@app.post("/api/book_channel/{channel_id}")
async def book_channel(channel_id: int) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "book_channel",
        "channel_id": channel_id,
        "reservation_id": f"res-{channel_id}",
    }


@app.post("/api/change_owner/{channel_id}")
async def change_owner(channel_id: int) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "change_owner",
        "channel_id": channel_id,
        "ownership_transfer": "started",
    }


@app.post("/api/create_channel")
async def create_channel(payload: CreateChannelRequest) -> Dict[str, Any]:
    return {
        "status": "stub",
        "action": "create_channel",
        "account_schedule": (
            {
                "triggered": True,
                "endpoint": "/api/add_account_schedule/{account_id}",
                "account_id": payload.account_id,
            }
            if payload.account_id is not None
            else {"triggered": False}
        ),
        "channel_service_call": {
            "endpoint": "/api/create_channel",
            "payload": {
                "title": payload.title,
                "topic": payload.topic,
                "language": payload.language,
            },
        },
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
