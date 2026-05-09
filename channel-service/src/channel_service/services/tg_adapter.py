import requests

from channel_service.core.config import Config


def _post_json(url: str, payload: dict) -> dict:
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


async def create_telegram_channel(title: str, description: str) -> dict:
    url = f"{Config.TG_ADAPTER_CHANNEL_URL}/api/create_tg_channel"
    payload = {"title": title, "about": description or ""}
    data = _post_json(url, payload)
    return {
        "tg_channel_id": int(data["channel_id"]),
        "tg_access_hash": int(data["access_hash"]) if data.get("access_hash") is not None else None,
    }


async def change_telegram_owner(tg_channel_id: int, new_owner_id: int) -> dict:
    url = f"{Config.TG_ADAPTER_CHANNEL_URL}/api/change_owner/{tg_channel_id}"
    payload = {"new_owner_id": new_owner_id}
    return _post_json(url, payload)
