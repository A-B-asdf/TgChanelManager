import os
from typing import Optional, Tuple
from urllib.parse import urlparse

import socks
from telethon import TelegramClient
from telethon.tl.functions.channels import (
    CreateChannelRequest,
    DeleteChannelRequest,
    EditAdminRequest,
    GetFullChannelRequest,
    GetParticipantRequest,
    LeaveChannelRequest,
)
from telethon.tl.functions.messages import ExportChatInviteRequest
from telethon.tl.types import ChatAdminRights, InputChannel, InputPeerChannel, InputUser

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


def _input_channel(channel_id: int, access_hash: Optional[int] = None):
    """Build an InputChannel for Telethon channels.* requests.

Important: channels.DeleteChannelRequest, LeaveChannelRequest,
EditAdminRequest and GetParticipantRequest expect InputChannel, not
InputPeerChannel. Using InputPeerChannel may work for some API calls,
but can fail with 500-level errors in our adapter when deleting channels.
"""
    if access_hash is not None:
        return InputChannel(channel_id=int(channel_id), access_hash=int(access_hash))
    return int(channel_id)


def _input_peer(channel_id: int, access_hash: Optional[int] = None):
    """Build an InputPeerChannel for messages.* requests such as invite export."""
    if access_hash is not None:
        return InputPeerChannel(channel_id=int(channel_id), access_hash=int(access_hash))
    return int(channel_id)


def _full_admin_rights() -> ChatAdminRights:
    return ChatAdminRights(
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


async def _input_user_from_joined_participant(client_g, channel_peer, user_id: int):
    """Resolve a user who has already joined this channel into an InputUser."""
    try:
        participant = await client_g(GetParticipantRequest(channel=channel_peer, participant=int(user_id)))
    except Exception as exc:
        raise RuntimeError(
            "Пользователь ещё не найден среди участников канала. "
            "Пусть он сначала перейдёт по invite-ссылке и вступит в канал, затем снова нажмёт подтверждение."
        ) from exc

    for user in getattr(participant, "users", []) or []:
        if int(getattr(user, "id", 0)) == int(user_id):
            access_hash = getattr(user, "access_hash", None)
            if access_hash is not None:
                return InputUser(user_id=int(user.id), access_hash=int(access_hash))
            return int(user.id)
    return int(user_id)


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


async def create_channel_invite_link(channel_id: int, access_hash: Optional[int] = None) -> dict:
    client_g = await get_client()
    peer = _input_peer(channel_id, access_hash)
    invite = await client_g(ExportChatInviteRequest(peer=peer))
    link = getattr(invite, "link", None)
    if not link:
        raise RuntimeError("Telegram did not return invite link")
    return {"invite_link": link, "channel_id": int(channel_id)}


async def delete_telegram_channel(channel_id: int, access_hash: Optional[int] = None) -> dict:
    """Delete a Telegram channel/supergroup.

    Telegram allows this only for an account with enough rights, usually the owner.
    If the admin account has already left the channel after handoff, this call will fail.
    """
    client_g = await get_client()
    peer = _input_channel(channel_id, access_hash)
    await client_g(DeleteChannelRequest(channel=peer))
    return {"status": "deleted", "channel_id": int(channel_id)}


async def leave_telegram_channel(channel_id: int, access_hash: Optional[int] = None) -> dict:
    client_g = await get_client()
    peer = _input_channel(channel_id, access_hash)
    await client_g(LeaveChannelRequest(channel=peer))
    return {"status": "left", "channel_id": int(channel_id)}


async def finalize_channel_transfer(
    channel_id: int,
    access_hash: Optional[int],
    requester_account_id: int,
    leave_after_admin: bool = True,
) -> dict:
    """Promote buyer after they joined the channel, then try to leave as the admin account.

    This is intentionally a two-step handoff: invite link first, confirmation after the buyer joins.
    Otherwise Telegram cannot promote a user that is not yet a channel participant.
    """
    client_g = await get_client()
    peer = _input_channel(channel_id, access_hash)
    input_user = await _input_user_from_joined_participant(client_g, peer, requester_account_id)

    await client_g(
        EditAdminRequest(
            channel=peer,
            user_id=input_user,
            admin_rights=_full_admin_rights(),
            rank="Admin",
        )
    )

    admin_left = False
    leave_error = None
    if leave_after_admin:
        try:
            await client_g(LeaveChannelRequest(channel=peer))
            admin_left = True
        except Exception as exc:
            leave_error = str(exc)

    return {
        "status": "completed" if admin_left or not leave_after_admin else "promoted_admin_not_left",
        "channel_id": int(channel_id),
        "requester_account_id": int(requester_account_id),
        "buyer_promoted": True,
        "admin_left": admin_left,
        "leave_error": leave_error,
    }


async def change_channel_owner(channel_id: int, new_owner_id: int):
    client_g = await get_client()
    channel = await client_g.get_input_entity(channel_id)
    await client_g(
        EditAdminRequest(
            channel=channel,
            user_id=new_owner_id,
            admin_rights=_full_admin_rights(),
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
