from pydantic import BaseModel
from typing import Optional

class PostMessageRequest(BaseModel):
    channel_id: int
    access_hash: Optional[int] = None
    text: str
    parse_mode: Optional[str] = "HTML"
    media_url: Optional[str] = None

class ChangeMessageRequest(BaseModel):
    new_text: str
    channel_id: Optional[int] = None
    parse_mode: Optional[str] = "HTML"
