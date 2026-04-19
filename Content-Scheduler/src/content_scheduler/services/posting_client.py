import requests
from content_scheduler.core.config import Config

def send_to_posting_service(channel_id: int, text: str) -> dict:
    url = f"{Config.POSTING_SERVICE_URL}/api/post_msg/"
    payload = {
        "channel_id": channel_id,
        "text": text,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    return response.json()