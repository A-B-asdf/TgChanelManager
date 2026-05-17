import requests

from channel_service.core.config import Config


def _post_json(url: str, payload: dict) -> dict:
    resp = requests.post(url, json=payload, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"{resp.status_code} error from {url}: {resp.text}")
    return resp.json()


async def create_telegram_channel(title: str, description: str) -> dict:
    url = f"{Config.TG_ADAPTER_CHANNEL_URL}/api/create_tg_channel"
    payload = {"title": title, "about": description or ""}
    data = _post_json(url, payload)
    return {
        "tg_channel_id": int(data["channel_id"]),
        "tg_access_hash": int(data["access_hash"]) if data.get("access_hash") is not None else None,
    }


async def create_telegram_invite_link(tg_channel_id: int, tg_access_hash: int | None = None) -> dict:
    url = f"{Config.TG_ADAPTER_CHANNEL_URL}/api/create_invite_link"
    payload = {"channel_id": tg_channel_id, "access_hash": tg_access_hash}
    return _post_json(url, payload)


async def change_telegram_owner(tg_channel_id: int, new_owner_id: int) -> dict:
    url = f"{Config.TG_ADAPTER_CHANNEL_URL}/api/change_owner/{tg_channel_id}"
    payload = {"new_owner_id": new_owner_id}
    return _post_json(url, payload)


async def leave_telegram_channel(tg_channel_id: int, tg_access_hash: int | None = None) -> dict:
    url = f"{Config.TG_ADAPTER_CHANNEL_URL}/api/leave_channel"
    payload = {"channel_id": tg_channel_id, "access_hash": tg_access_hash}
    return _post_json(url, payload)


async def finalize_telegram_transfer(
    tg_channel_id: int,
    requester_account_id: int,
    tg_access_hash: int | None = None,
    leave_after_admin: bool = True,
) -> dict:
    url = f"{Config.TG_ADAPTER_CHANNEL_URL}/api/finalize_channel_transfer"
    payload = {
        "channel_id": tg_channel_id,
        "access_hash": tg_access_hash,
        "requester_account_id": requester_account_id,
        "leave_after_admin": leave_after_admin,
    }
    return _post_json(url, payload)


async def delete_telegram_channel(tg_channel_id: int, tg_access_hash: int | None = None) -> dict:
    url = f"{Config.TG_ADAPTER_CHANNEL_URL}/api/delete_channel"
    payload = {"channel_id": tg_channel_id, "access_hash": tg_access_hash}
    return _post_json(url, payload)
