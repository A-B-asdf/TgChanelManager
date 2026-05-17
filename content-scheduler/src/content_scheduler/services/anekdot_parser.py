from typing import List

from content_scheduler.services.content_sources import fetch_anekdots


def fetch_anekdot() -> str:
    return fetch_anekdots(limit=1)[0]
