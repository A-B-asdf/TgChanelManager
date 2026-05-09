import requests

from fulfillment_service.core.config import Config


def _post_json(url: str, payload: dict) -> dict:
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


async def call_channel_service_create(title: str, description: str, account_id: int) -> dict:
    url = f"{Config.CHANNEL_SERVICE_URL}/api/create_channel"
    payload = {"title": title, "description": description, "account_id": account_id}
    return _post_json(url, payload)


async def call_channel_service_change_owner(channel_id: int, new_owner_id: int) -> dict:
    url = f"{Config.CHANNEL_SERVICE_URL}/api/change_owner/{channel_id}"
    payload = {"new_owner_id": new_owner_id}
    return _post_json(url, payload)
