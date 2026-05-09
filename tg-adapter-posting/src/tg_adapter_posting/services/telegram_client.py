import os
from typing import Optional, Tuple
from urllib.parse import urlparse

import socks
from telethon import TelegramClient
from telethon.tl.types import InputPeerChannel

api_id_raw = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
session_file = os.getenv("TELEGRAM_SESSION_FILE", "/app/sessions/posting.session")

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
        await client.start(phone=os.getenv("TELEGRAM_POSTING_ACCOUNT_PHONE") or os.getenv("TELEGRAM_CHANNEL_ACCOUNT_PHONE"))
    return client


async def _resolve_channel_entity(client_g, channel_id: int, access_hash: Optional[int] = None):
    if access_hash is not None:
        return InputPeerChannel(channel_id=int(channel_id), access_hash=int(access_hash))
    # Fallback for public channels or entities already cached in this session.
    return await client_g.get_input_entity(channel_id)


async def send_telegram_message(channel_id: int, text: str, parse_mode: str, access_hash: Optional[int] = None) -> int:
    client_g = await get_client()
    entity = await _resolve_channel_entity(client_g, channel_id, access_hash)
    result = await client_g.send_message(entity, text, parse_mode=parse_mode)
    return int(result.id)


async def edit_telegram_message(channel_id: int, msg_id: int, new_text: str, parse_mode: str):
    client_g = await get_client()
    entity = await _resolve_channel_entity(client_g, channel_id)
    await client_g.edit_message(entity, msg_id, new_text, parse_mode=parse_mode)
