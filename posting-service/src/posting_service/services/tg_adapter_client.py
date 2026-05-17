import requests

from posting_service.core.config import Config


def call_tg_adapter_post_message(channel_id: int, text: str, parse_mode: str, access_hash: int = None, media_url: str = None) -> dict:
    url = f"{Config.TG_ADAPTER_POSTING_URL}/api/post_msg/"
    payload = {
        "channel_id": channel_id,
        "access_hash": access_hash,
        "text": text,
        "parse_mode": parse_mode,
        "media_url": media_url,
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def call_tg_adapter_change_message(msg_id: int, new_text: str, parse_mode: str, channel_id: int) -> dict:
    url = f"{Config.TG_ADAPTER_POSTING_URL}/api/change_msg/{msg_id}"
    payload = {
        "new_text": new_text,
        "parse_mode": parse_mode,
        "channel_id": channel_id,
    }
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
