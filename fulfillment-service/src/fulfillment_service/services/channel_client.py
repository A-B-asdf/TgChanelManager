import requests

from fulfillment_service.core.config import Config


def _post_json(url: str, payload: dict) -> dict:
    response = requests.post(url, json=payload, timeout=30)
    if not response.ok:
        raise RuntimeError(f"{response.status_code} error from {url}: {response.text}")
    return response.json()


async def call_channel_service_create(title: str, description: str, account_id: int) -> dict:
    url = f"{Config.CHANNEL_SERVICE_URL}/api/create_channel"
    return _post_json(url, {"title": title, "description": description, "account_id": account_id})


async def call_channel_service_change_owner(channel_id: int, new_owner_id: int) -> dict:
    url = f"{Config.CHANNEL_SERVICE_URL}/api/change_owner/{channel_id}"
    return _post_json(url, {"new_owner_id": new_owner_id})


async def call_channel_service_create_invite_link(channel_id: int) -> dict:
    url = f"{Config.CHANNEL_SERVICE_URL}/api/create_invite_link/{channel_id}"
    return _post_json(url, {})


async def call_channel_service_finalize_transfer(channel_id: int, requester_account_id: int, leave_after_admin: bool = True) -> dict:
    url = f"{Config.CHANNEL_SERVICE_URL}/api/finalize_transfer/{channel_id}"
    return _post_json(
        url,
        {
            "requester_account_id": requester_account_id,
            "leave_after_admin": leave_after_admin,
        },
    )


async def call_channel_service_delete(channel_id: int, delete_in_telegram: bool = True, force_metadata_delete: bool = False) -> dict:
    url = f"{Config.CHANNEL_SERVICE_URL}/api/delete_channel/{channel_id}"
    return _post_json(
        url,
        {
            "delete_in_telegram": delete_in_telegram,
            "force_metadata_delete": force_metadata_delete,
        },
    )
