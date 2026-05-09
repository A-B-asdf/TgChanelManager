import os
from typing import Optional, Tuple
from urllib.parse import urlparse

import socks
from telethon import TelegramClient
from telethon.tl.functions.channels import CreateChannelRequest, EditAdminRequest, GetFullChannelRequest
from telethon.tl.types import ChatAdminRights

api_id_raw = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
session_file = os.getenv("TELEGRAM_SESSION_FILE", "/app/sessions/channel.session")

if not api_id_raw or not api_hash:
    raise RuntimeError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")
api_id = int(api_id_raw)

client = None


def _build_proxy() -> Optional[Tuple]:
    proxy_url = os.getenv("PROXY_URL") or os.getenv("ALL_PROXY") or os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY")
    if not proxy_url:
        return None

    parsed = urlparse(proxy_url)
    scheme = parsed.scheme.lower()
    if scheme in {"socks5", "socks5h"}:
        proxy_type = socks.SOCKS5
    elif scheme in {"socks4", "socks4a"}:
        proxy_type = socks.SOCKS4
    elif scheme in {"http", "https"}:
        proxy_type = socks.HTTP
    else:
        raise RuntimeError(f"Unsupported proxy scheme: {scheme}")

    username = parsed.username or os.getenv("PROXY_USER")
    password = parsed.password or os.getenv("PROXY_PASSWORD")
    return (proxy_type, parsed.hostname, parsed.port, True, username, password)


async def get_client():
    global client
    if client is None:
        os.makedirs(os.path.dirname(session_file), exist_ok=True)
        client = TelegramClient(session_file, api_id, api_hash, proxy=_build_proxy())
        await client.start(phone=os.getenv("TELEGRAM_CHANNEL_ACCOUNT_PHONE"))
    return client


async def create_telegram_channel(title: str, about: str = None) -> dict:
    client_g = await get_client()
    result = await client_g(
        CreateChannelRequest(
            title=title,
            about=about or "",
            megagroup=False,
        )
    )
    channel = result.chats[0]
    return {
        "channel_id": int(channel.id),
        "access_hash": int(channel.access_hash) if getattr(channel, "access_hash", None) is not None else None,
        "title": getattr(channel, "title", title),
    }


async def change_channel_owner(channel_id: int, new_owner_id: int):
    client_g = await get_client()
    channel = await client_g.get_input_entity(channel_id)
    rights = ChatAdminRights(
        change_info=True,
        post_messages=True,
        edit_messages=True,
        delete_messages=True,
        ban_users=True,
        invite_users=True,
        pin_messages=True,
        add_admins=True,
        anonymous=False,
        manage_call=True,
        other=True,
    )
    await client_g(
        EditAdminRequest(
            channel=channel,
            user_id=new_owner_id,
            admin_rights=rights,
            rank="Admin",
        )
    )


async def get_channel_info(channel_id: int):
    client_g = await get_client()
    entity = await client_g.get_input_entity(channel_id)
    full = await client_g(GetFullChannelRequest(channel=entity))
    return {
        "id": full.full_chat.id,
        "title": full.chats[0].title,
        "participants_count": full.full_chat.participants_count,
        "about": full.full_chat.about,
        "username": full.chats[0].username,
    }


async def get_channel_statistic(channel_id: int):
    info = await get_channel_info(channel_id)
    return {
        "subscribers": info["participants_count"],
        "channel_id": info["id"],
        "title": info["title"],
    }
