import requests
from posting_service.core.config import Config

def call_tg_adapter_post_message(channel_id: int, text: str, parse_mode: str) -> dict:
    url = f"{Config.TG_ADAPTER_URL}/api/post_msg/"
    payload = {
        "channel_id": channel_id,
        "text": text,
        "parse_mode": parse_mode
    }
    response = requests.post(url, json=payload)
    return response.json()

def call_tg_adapter_change_message(msg_id: int, new_text: str, parse_mode: str, channel_id: int = None) -> dict:
    url = f"{Config.TG_ADAPTER_URL}/api/change_msg/{msg_id}"
    payload = {
        "new_text": new_text,
        "parse_mode": parse_mode,
        "channel_id": channel_id
    }
    response = requests.post(url, json=payload)
    return response.json()