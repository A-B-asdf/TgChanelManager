from pydantic import BaseModel
from typing import Optional

class PostMessageRequest(BaseModel):
    channel_id: int
    text: str
    parse_mode: Optional[str] = "HTML"

class ChangeMessageRequest(BaseModel):
    new_text: str
    channel_id: Optional[int] = None
    parse_mode: Optional[str] = "HTML"