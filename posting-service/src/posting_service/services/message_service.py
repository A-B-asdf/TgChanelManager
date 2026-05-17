from posting_service.core.database import log_sent_message
from posting_service.services.tg_adapter_client import call_tg_adapter_change_message, call_tg_adapter_post_message


def send_message(channel_id: int, text: str, parse_mode: str, access_hash: int = None, media_url: str = None) -> dict:
    resp = call_tg_adapter_post_message(channel_id, text, parse_mode, access_hash, media_url=media_url)
    success = resp.get("status") == "sent"
    log_sent_message(
        channel_id=channel_id,
        platform="telegram",
        external_id=resp.get("message_id"),
        text_preview=text[:50],
        status=resp.get("status", "failed"),
    )
    return {
        "status": "sent" if success else "failed",
        "message_id": resp.get("message_id"),
        "channel_id": channel_id,
        "text_preview": text[:50],
        "has_media": bool(media_url),
    }


def edit_message(msg_id: int, new_text: str, parse_mode: str, channel_id: int) -> dict:
    resp = call_tg_adapter_change_message(msg_id, new_text, parse_mode, channel_id)
    return {"status": resp.get("status"), "message_id": msg_id, "channel_id": channel_id}
