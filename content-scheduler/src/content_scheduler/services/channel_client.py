import logging
from typing import Dict, List

import requests

from content_scheduler.core.config import Config

logger = logging.getLogger(__name__)


def get_channels_by_account(account_id: int) -> List[Dict]:
    url = f"{Config.FULFILLMENT_SERVICE_URL}/api/get_all_channel"
    try:
        response = requests.get(url, params={"account_id": account_id}, timeout=10)
        response.raise_for_status()
        data = response.json()
        channels = data.get("items", [])
        result = []
        for ch in channels:
            tg_channel_id = ch.get("tg_channel_id")
            if not tg_channel_id:
                continue
            result.append({
                "channel_id": int(tg_channel_id),
                "access_hash": int(ch["tg_access_hash"]) if ch.get("tg_access_hash") is not None else None,
                "title": ch.get("title"),
            })
        return result
    except Exception as exc:
        logger.exception("Error getting channels for account %s: %s", account_id, exc)
        return []
