from typing import Optional

import requests

from content_scheduler.core.config import Config


def send_to_posting_service(channel_id: int, text: str, access_hash: Optional[int] = None, media_url: Optional[str] = None) -> dict:
    url = f"{Config.POSTING_SERVICE_URL}/api/post_msg/"
    payload = {
        "channel_id": channel_id,
        "access_hash": access_hash,
        "text": text,
        "parse_mode": "HTML",
        "media_url": media_url,
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()
