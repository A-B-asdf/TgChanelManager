import os
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        return default


def _int_list_env(name: str) -> List[int]:
    raw = os.getenv(name, "").strip()
    result: List[int] = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            result.append(int(part))
        except ValueError:
            pass
    return result


class Config:
    DB_PATH = os.getenv("SCHEDULER_DB_PATH", "/app/data/scheduler.db")
    POSTING_SERVICE_URL = os.getenv("POSTING_SERVICE_URL", "http://localhost:8001")
    FULFILLMENT_SERVICE_URL = os.getenv("FULFILLMENT_SERVICE_URL", "http://localhost:8003")
    REQUEST_TIMEOUT = _int_env("REQUEST_TIMEOUT", 120)

    # Content sources. Channels have a content_type and the scheduler selects the source by that type.
    ANEKDOT_URL = os.getenv("ANEKDOT_URL", "https://www.anekdot.ru/random/anekdot/")
    NEWS_RSS_URL = os.getenv("NEWS_RSS_URL", "https://lenta.ru/rss/news")
    SPORT_RSS_URL = os.getenv("SPORT_RSS_URL", "https://www.sports.ru/rss/all_news.xml")
    STEAM_FEATURED_URL = os.getenv("STEAM_FEATURED_URL", "https://store.steampowered.com/api/featuredcategories?cc=ru&l=russian")
    RECIPE_RANDOM_URL = os.getenv("RECIPE_RANDOM_URL", "")
    MEME_API_URL = os.getenv("MEME_API_URL", "https://meme-api.com/gimme")
    CAT_API_URL = os.getenv("CAT_API_URL", "https://api.thecatapi.com/v1/images/search")
    ITUNES_SEARCH_URL = os.getenv("ITUNES_SEARCH_URL", "https://itunes.apple.com/search")
    ITUNES_LOOKUP_URL = os.getenv("ITUNES_LOOKUP_URL", "https://itunes.apple.com/lookup")
    ITUNES_COUNTRY = os.getenv("ITUNES_COUNTRY", "US")
    MUSIC_SEARCH_TERMS = os.getenv("MUSIC_SEARCH_TERMS", "")

    # Hourly autopost defaults.
    DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")
    HOURLY_CRON = os.getenv("HOURLY_CRON", "0 * * * *")
    ADMIN_USER_IDS = _int_list_env("ADMIN_USER_IDS")

    # If true, content-scheduler creates hourly schedules for ADMIN_USER_IDS automatically.
    # This avoids the common case when /publish_now works, but /schedule was never pressed.
    AUTO_CREATE_ADMIN_SCHEDULES = _bool_env("AUTO_CREATE_ADMIN_SCHEDULES", True)

    # If true, content-scheduler publishes once after restart, because Windows/Docker cannot
    # execute missed jobs while the PC was turned off.
    PUBLISH_ON_STARTUP = _bool_env("PUBLISH_ON_STARTUP", True)

    # Safety net: every 30 seconds checks whether an hourly schedule should have fired.
    # It uses a DB lock, so APScheduler and watchdog will not double-post the same hour.
    SCHEDULE_WATCHDOG_ENABLED = _bool_env("SCHEDULE_WATCHDOG_ENABLED", True)
