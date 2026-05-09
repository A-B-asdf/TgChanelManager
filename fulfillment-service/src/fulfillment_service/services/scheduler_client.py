import requests

from fulfillment_service.core.config import Config


async def add_account_schedule(account_id: int, cron: str):
    url = f"{Config.CONTENT_SCHEDULER_URL}/api/add_account_schedule/{account_id}"
    payload = {"cron": cron, "timezone": "Europe/Moscow", "active": True}
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
