import asyncio
import os
from typing import Optional, Tuple
from urllib.parse import urlparse

import socks
from telethon import TelegramClient


def build_proxy() -> Optional[Tuple]:
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
    return (
        proxy_type,
        parsed.hostname,
        parsed.port,
        True,
        parsed.username or os.getenv("PROXY_USER"),
        parsed.password or os.getenv("PROXY_PASSWORD"),
    )


async def main() -> None:
    api_id = int(os.environ["TELEGRAM_API_ID"])
    api_hash = os.environ["TELEGRAM_API_HASH"]
    session_file = os.getenv("TELEGRAM_SESSION_FILE", "/app/sessions/posting.session")
    phone = os.getenv("TELEGRAM_POSTING_ACCOUNT_PHONE") or os.getenv("TELEGRAM_CHANNEL_ACCOUNT_PHONE") or os.getenv("TELEGRAM_PHONE")

    os.makedirs(os.path.dirname(session_file), exist_ok=True)

    client = TelegramClient(session_file, api_id, api_hash, proxy=build_proxy())
    try:
        await client.start(phone=phone)
        me = await client.get_me()
        username_or_id = getattr(me, "username", None) or getattr(me, "id", "unknown")
        print(f"Session created for @{username_or_id}: {session_file}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
