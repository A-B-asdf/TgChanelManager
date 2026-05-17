import html
import random
import re
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from content_scheduler.core.config import Config

CONTENT_TYPES: Dict[str, str] = {
    "jokes": "Анекдоты",
    "news": "Новости",
    "sport": "Спорт",
    "games": "Игры",
    "recipes": "Рецепты",
    "memes": "Мемы",
    "cats": "Котики",
    "music": "Музыка",
}


class ContentSourceError(RuntimeError):
    pass


def normalize_content_type(value: Optional[str]) -> str:
    value = (value or "jokes").strip().lower()
    return value if value in CONTENT_TYPES else "jokes"


def content_type_label(value: Optional[str]) -> str:
    return CONTENT_TYPES.get(normalize_content_type(value), CONTENT_TYPES["jokes"])


def _clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    value = BeautifulSoup(value, "lxml").get_text(" ", strip=True)
    value = html.unescape(value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _shorten(value: str, limit: int = 900) -> str:
    value = value.strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def fetch_anekdots(limit: int = 20) -> List[str]:
    response = requests.get(Config.ANEKDOT_URL, timeout=Config.REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    blocks = soup.find_all("div", class_="text")
    result: List[str] = []
    for block in blocks:
        text = block.get_text("\n", strip=True)
        if text and text not in result:
            result.append(text)
        if len(result) >= limit:
            break
    if not result:
        raise ContentSourceError(f"Анекдоты не найдены на странице {Config.ANEKDOT_URL}")
    return result


def _fetch_rss_items(url: str, limit: int = 20) -> List[Dict[str, str]]:
    response = requests.get(url, timeout=Config.REQUEST_TIMEOUT, headers={"User-Agent": "tg-channel-manager/1.0"})
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = root.findall(".//item")
    if not items:
        # Atom feeds use entry/title/link/summary.
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        entries = root.findall(".//atom:entry", ns)
        result: List[Dict[str, str]] = []
        for entry in entries[:limit]:
            title = _clean_text((entry.findtext("atom:title", default="", namespaces=ns)))
            summary = _clean_text((entry.findtext("atom:summary", default="", namespaces=ns)))
            link_el = entry.find("atom:link", ns)
            link = link_el.attrib.get("href", "") if link_el is not None else ""
            if title:
                result.append({"title": title, "description": summary, "link": link})
        return result

    result = []
    for item in items[:limit]:
        title = _clean_text(item.findtext("title"))
        description = _clean_text(item.findtext("description"))
        link = _clean_text(item.findtext("link"))
        if title:
            result.append({"title": title, "description": description, "link": link})
    return result


def _format_rss_post(prefix: str, item: Dict[str, str]) -> str:
    title = item.get("title", "").strip()
    description = item.get("description", "").strip()
    link = item.get("link", "").strip()
    parts = [prefix, f"<b>{html.escape(title)}</b>"]
    if description:
        parts.append(html.escape(_shorten(description, 450)))
    if link:
        parts.append(link)
    return "\n\n".join(parts)


def fetch_news(limit: int = 20) -> List[str]:
    items = _fetch_rss_items(Config.NEWS_RSS_URL, limit=limit)
    result = [_format_rss_post("📰 Новость", item) for item in items]
    if not result:
        raise ContentSourceError(f"Новости не найдены в RSS {Config.NEWS_RSS_URL}")
    return result


def fetch_sport(limit: int = 20) -> List[str]:
    try:
        items = _fetch_rss_items(Config.SPORT_RSS_URL, limit=limit)
        result = [_format_rss_post("🏆 Спорт", item) for item in items]
        if result:
            return result
    except Exception:
        # Fallback below keeps the channel alive if the external RSS endpoint is unavailable.
        pass

    teams = [
        "Зенит — футбольный клуб из Санкт-Петербурга, один из самых титулованных клубов России.",
        "Спартак — московский футбольный клуб с большой историей и одной из самых крупных фан-баз.",
        "ЦСКА — спортивный клуб, известный футбольной, хоккейной и баскетбольной командами.",
        "Локомотив — московский клуб, традиционно ассоциирующийся с железнодорожной историей.",
        "Ак Барс — хоккейный клуб из Казани, один из сильнейших клубов КХЛ.",
        "СКА — хоккейный клуб из Санкт-Петербурга, один из лидеров российского хоккея.",
        "Лос-Анджелес Лейкерс — легендарный баскетбольный клуб NBA.",
        "Манчестер Сити — английский футбольный клуб, известный атакующим стилем игры.",
        "Реал Мадрид — один из самых титулованных футбольных клубов мира.",
        "Барселона — испанский клуб, известный академией и атакующей философией игры.",
    ]
    random.shuffle(teams)
    return [f"🏆 Спортивная рекомендация\n\n{team}" for team in teams[:limit]]


def fetch_games(limit: int = 20) -> List[str]:
    try:
        response = requests.get(Config.STEAM_FEATURED_URL, timeout=Config.REQUEST_TIMEOUT, headers={"User-Agent": "tg-channel-manager/1.0"})
        response.raise_for_status()
        data = response.json()
        games: List[Dict[str, Any]] = []
        for category in data.values():
            if isinstance(category, dict) and isinstance(category.get("items"), list):
                games.extend([item for item in category["items"] if isinstance(item, dict) and item.get("name")])
        random.shuffle(games)
        result = []
        for game in games[:limit]:
            name = html.escape(str(game.get("name", "Игра")))
            discount = game.get("discount_percent") or 0
            url = game.get("url") or ""
            line = f"🎮 Игра дня\n\n<b>{name}</b>"
            if discount:
                line += f"\nСкидка: {discount}%"
            if url:
                line += f"\n{url}"
            result.append(line)
        if result:
            return result
    except Exception:
        pass

    fallback = [
        "🎮 Игра дня\n\n<b>Stardew Valley</b>\nУютная фермерская игра с развитием хозяйства, крафтом и исследованием.",
        "🎮 Игра дня\n\n<b>Hades</b>\nДинамичный roguelike с сильным сюжетом и быстрыми боями.",
        "🎮 Игра дня\n\n<b>Portal 2</b>\nГоловоломка с порталами, юмором и отличной кооперативной кампанией.",
        "🎮 Игра дня\n\n<b>Civilization VI</b>\nСтратегия, где можно развивать цивилизацию от древности до будущего.",
        "🎮 Игра дня\n\n<b>Hollow Knight</b>\nАтмосферная метроидвания с исследованием большого подземного мира.",
    ]
    random.shuffle(fallback)
    return fallback[:limit]


def fetch_recipes(limit: int = 20) -> List[str]:
    """Return Russian-language recipe posts.

    The previous default source was TheMealDB, which often returns English names,
    ingredients and instructions. For the demo bot we keep recipes fully in Russian
    by using a built-in catalog and shuffling it on every request. If you later add
    a Russian recipe API, this function can be swapped without changing the rest of
    the posting chain.
    """
    recipes = [
        {
            "name": "Куриный суп с лапшой",
            "category": "Первое блюдо",
            "time": "35–45 минут",
            "ingredients": ["куриное филе", "лапша", "морковь", "лук", "картофель", "зелень", "соль", "перец"],
            "steps": "Сварите куриный бульон, добавьте картофель, морковь и лук. За 7–10 минут до готовности положите лапшу и нарезанную курицу. Подавайте с зеленью.",
        },
        {
            "name": "Паста с томатами и базиликом",
            "category": "Горячее",
            "time": "20 минут",
            "ingredients": ["паста", "томаты", "чеснок", "базилик", "оливковое масло", "твёрдый сыр"],
            "steps": "Отварите пасту до состояния аль денте. На масле прогрейте чеснок и томаты, смешайте с пастой, добавьте базилик и посыпьте сыром.",
        },
        {
            "name": "Омлет с сыром и зеленью",
            "category": "Завтрак",
            "time": "10 минут",
            "ingredients": ["яйца", "молоко", "сыр", "укроп", "соль", "сливочное масло"],
            "steps": "Взбейте яйца с молоком и солью. Вылейте на сковороду, добавьте сыр и зелень, готовьте под крышкой на слабом огне.",
        },
        {
            "name": "Гречка с грибами",
            "category": "Гарнир",
            "time": "30 минут",
            "ingredients": ["гречка", "шампиньоны", "лук", "морковь", "растительное масло", "соль"],
            "steps": "Отварите гречку. Обжарьте лук, морковь и грибы, затем смешайте с кашей и прогрейте всё вместе 3–5 минут.",
        },
        {
            "name": "Салат с курицей и огурцом",
            "category": "Салат",
            "time": "20 минут",
            "ingredients": ["куриная грудка", "огурец", "яйца", "сыр", "йогурт или майонез", "зелень"],
            "steps": "Отварите курицу и яйца, нарежьте все ингредиенты кубиками, заправьте йогуртом или майонезом и перемешайте.",
        },
        {
            "name": "Картофель по-деревенски",
            "category": "Гарнир",
            "time": "40 минут",
            "ingredients": ["картофель", "паприка", "чеснок", "растительное масло", "соль", "перец"],
            "steps": "Нарежьте картофель дольками, смешайте с маслом и специями. Запекайте при 200 °C до румяной корочки.",
        },
        {
            "name": "Творожная запеканка",
            "category": "Десерт",
            "time": "45 минут",
            "ingredients": ["творог", "яйца", "манка", "сахар", "сметана", "ваниль"],
            "steps": "Смешайте творог, яйца, манку и сахар. Выложите в форму, смажьте сметаной и запекайте до золотистой корочки.",
        },
        {
            "name": "Рис с овощами",
            "category": "Горячее",
            "time": "25 минут",
            "ingredients": ["рис", "болгарский перец", "морковь", "зелёный горошек", "лук", "соевый соус"],
            "steps": "Отварите рис. Овощи быстро обжарьте, добавьте рис и немного соевого соуса, перемешайте и прогрейте.",
        },
        {
            "name": "Сырники на сковороде",
            "category": "Завтрак",
            "time": "25 минут",
            "ingredients": ["творог", "яйцо", "мука", "сахар", "ваниль", "масло для жарки"],
            "steps": "Смешайте творог, яйцо, сахар и немного муки. Сформируйте сырники, обжарьте с двух сторон до румяности.",
        },
        {
            "name": "Овощное рагу",
            "category": "Горячее",
            "time": "35 минут",
            "ingredients": ["кабачок", "картофель", "морковь", "лук", "томаты", "чеснок", "зелень"],
            "steps": "Нарежьте овощи, обжарьте лук и морковь, добавьте остальные овощи и тушите под крышкой до мягкости.",
        },
        {
            "name": "Блины на молоке",
            "category": "Завтрак / десерт",
            "time": "30 минут",
            "ingredients": ["молоко", "яйца", "мука", "сахар", "соль", "растительное масло"],
            "steps": "Смешайте молоко, яйца, муку, сахар и соль до жидкого теста. Добавьте масло и жарьте тонкие блины на хорошо разогретой сковороде.",
        },
        {
            "name": "Курица в сливочном соусе",
            "category": "Горячее",
            "time": "30 минут",
            "ingredients": ["куриное филе", "сливки", "чеснок", "сыр", "соль", "перец", "петрушка"],
            "steps": "Обжарьте курицу кусочками, добавьте чеснок и сливки. Тушите 10 минут, посыпьте сыром и зеленью.",
        },
        {
            "name": "Салат с тунцом",
            "category": "Салат",
            "time": "15 минут",
            "ingredients": ["консервированный тунец", "яйца", "огурец", "листья салата", "кукуруза", "оливковое масло"],
            "steps": "Нарежьте яйца и огурец, добавьте тунец, кукурузу и салатные листья. Заправьте маслом и аккуратно перемешайте.",
        },
        {
            "name": "Томатный суп-пюре",
            "category": "Первое блюдо",
            "time": "30 минут",
            "ingredients": ["томаты", "лук", "чеснок", "бульон", "сливки", "базилик", "сухарики"],
            "steps": "Потушите томаты с луком и чесноком, добавьте бульон и пробейте блендером. Влейте сливки и подавайте с сухариками.",
        },
        {
            "name": "Запечённая рыба с лимоном",
            "category": "Горячее",
            "time": "25 минут",
            "ingredients": ["филе рыбы", "лимон", "оливковое масло", "соль", "перец", "укроп"],
            "steps": "Посолите рыбу, добавьте лимон и масло. Запекайте при 180 °C 15–20 минут, подавайте с зеленью.",
        },
    ]
    random.shuffle(recipes)
    result: List[str] = []
    for recipe in recipes[:limit]:
        ingredients = ", ".join(recipe["ingredients"])
        post = (
            "🍽 Рецепт дня\n\n"
            f"<b>{html.escape(recipe['name'])}</b>\n"
            f"Категория: {html.escape(recipe['category'])}\n"
            f"Время приготовления: {html.escape(recipe['time'])}\n\n"
            f"Ингредиенты: {html.escape(ingredients)}\n\n"
            f"Как готовить: {html.escape(recipe['steps'])}"
        )
        result.append(post)
    return result



def fetch_memes(limit: int = 20) -> List[Dict[str, Any]]:
    """Return random memes with an optional image URL.

    The source returns a random Reddit meme. We keep a text fallback with the original post
    link so the posting chain still works if Telegram cannot fetch the image URL.
    """
    result: List[Dict[str, Any]] = []
    attempts = max(limit, 5)
    seen_urls = set()
    for _ in range(attempts):
        try:
            response = requests.get(Config.MEME_API_URL, timeout=Config.REQUEST_TIMEOUT, headers={"User-Agent": "tg-channel-manager/1.0"})
            response.raise_for_status()
            data = response.json()
            if data.get("nsfw"):
                continue
            title = _clean_text(data.get("title")) or "Случайный мем"
            subreddit = _clean_text(data.get("subreddit"))
            post_link = data.get("postLink") or ""
            image_url = data.get("url") or ""
            if image_url in seen_urls:
                continue
            seen_urls.add(image_url)
            text = f"😂 Мем дня\n\n<b>{html.escape(title)}</b>"
            if subreddit:
                text += f"\nИсточник: r/{html.escape(subreddit)}"
            if post_link:
                text += f"\n{post_link}"
            result.append({"text": text, "media_url": image_url or None})
            if len(result) >= limit:
                break
        except Exception:
            continue
    if result:
        return result

    fallback = [
        {"text": "😂 Мем дня\n\nКогда Docker finally up, но ты уже боишься смотреть logs.", "media_url": None},
        {"text": "😂 Мем дня\n\nЯ: сейчас быстро поправлю одну кнопку.\nПроект через час: v12-final-final.zip", "media_url": None},
        {"text": "😂 Мем дня\n\nАвтопостинг в 15:00: я в отпуске.", "media_url": None},
    ]
    random.shuffle(fallback)
    return fallback[:limit]


def fetch_cats(limit: int = 20) -> List[Dict[str, Any]]:
    """Return random cat images."""
    result: List[Dict[str, Any]] = []
    try:
        response = requests.get(
            Config.CAT_API_URL,
            params={"limit": min(max(limit, 1), 10), "mime_types": "jpg,png"},
            timeout=Config.REQUEST_TIMEOUT,
            headers={"User-Agent": "tg-channel-manager/1.0"},
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                image_url = item.get("url")
                if image_url:
                    result.append({"text": "🐱 Случайный котик", "media_url": image_url})
                if len(result) >= limit:
                    break
    except Exception:
        pass
    if result:
        return result

    fallback = [
        {"text": "🐱 Котик дня\n\nКартинка сейчас недоступна, но котик мысленно уже здесь.", "media_url": None},
        {"text": "🐱 Котик дня\n\nКот посмотрел на сервер и решил, что лучше поспать.", "media_url": None},
    ]
    random.shuffle(fallback)
    return fallback[:limit]


def _music_search_terms() -> List[str]:
    raw = getattr(Config, "MUSIC_SEARCH_TERMS", "") or ""
    terms = [part.strip() for part in raw.replace(";", ",").split(",") if part.strip()]
    if terms:
        return terms
    return [
        "rock", "pop", "jazz", "electronic", "indie", "metal", "hip hop", "soul",
        "queen", "daft punk", "radiohead", "nirvana", "the beatles", "michael jackson",
        "pink floyd", "arctic monkeys", "depeche mode", "the weeknd", "coldplay",
    ]


def _enlarge_itunes_artwork(url: str) -> str:
    # iTunes commonly returns 100x100 artwork. Larger versions usually work with this suffix change.
    return url.replace("100x100bb", "600x600bb").replace("100x100", "600x600")


def fetch_music(limit: int = 20) -> List[Dict[str, Any]]:
    """Return random album recommendation with artist, album and several tracks."""
    result: List[Dict[str, Any]] = []
    terms = _music_search_terms()
    random.shuffle(terms)
    for term in terms[: max(3, min(len(terms), 8))]:
        try:
            response = requests.get(
                Config.ITUNES_SEARCH_URL,
                params={"term": term, "entity": "album", "limit": 50, "country": Config.ITUNES_COUNTRY, "lang": "ru_ru"},
                timeout=Config.REQUEST_TIMEOUT,
                headers={"User-Agent": "tg-channel-manager/1.0"},
            )
            response.raise_for_status()
            albums = [item for item in response.json().get("results", []) if item.get("collectionId")]
            random.shuffle(albums)
            for album in albums:
                collection_id = album.get("collectionId")
                lookup = requests.get(
                    Config.ITUNES_LOOKUP_URL,
                    params={"id": collection_id, "entity": "song", "country": Config.ITUNES_COUNTRY, "lang": "ru_ru"},
                    timeout=Config.REQUEST_TIMEOUT,
                    headers={"User-Agent": "tg-channel-manager/1.0"},
                )
                lookup.raise_for_status()
                lookup_items = lookup.json().get("results", [])
                album_info = next((item for item in lookup_items if item.get("wrapperType") == "collection"), album)
                tracks = [item for item in lookup_items if item.get("wrapperType") == "track" and item.get("trackName")]

                artist = _clean_text(album_info.get("artistName")) or "Исполнитель"
                album_name = _clean_text(album_info.get("collectionName")) or "Альбом"
                genre = _clean_text(album_info.get("primaryGenreName"))
                release_date = str(album_info.get("releaseDate") or "")[:10]
                track_count = album_info.get("trackCount") or len(tracks)
                album_url = album_info.get("collectionViewUrl") or ""
                artwork_url = _enlarge_itunes_artwork(album_info.get("artworkUrl100") or "")

                random.shuffle(tracks)
                track_names = [_clean_text(track.get("trackName")) for track in tracks[:5]]
                track_names = [name for name in track_names if name]

                text = f"🎵 Музыкальная рекомендация\n\n<b>{html.escape(artist)} — {html.escape(album_name)}</b>"
                details = []
                if genre:
                    details.append(f"жанр: {genre}")
                if release_date:
                    details.append(f"релиз: {release_date}")
                if track_count:
                    details.append(f"треков: {track_count}")
                if details:
                    text += "\n" + html.escape("; ".join(details))
                if track_names:
                    text += "\n\nТреки:\n" + "\n".join(f"• {html.escape(name)}" for name in track_names)
                if album_url:
                    text += f"\n\n{album_url}"
                result.append({"text": text, "media_url": artwork_url or None})
                if len(result) >= limit:
                    return result
        except Exception:
            continue

    fallback = [
        {"text": "🎵 Музыкальная рекомендация\n\n<b>Daft Punk — Random Access Memories</b>\nжанр: Electronic; релиз: 2013; треков: 13\n\nТреки:\n• Give Life Back to Music\n• Get Lucky\n• Instant Crush", "media_url": None},
        {"text": "🎵 Музыкальная рекомендация\n\n<b>Queen — A Night at the Opera</b>\nжанр: Rock; релиз: 1975\n\nТреки:\n• Bohemian Rhapsody\n• Love of My Life\n• You're My Best Friend", "media_url": None},
        {"text": "🎵 Музыкальная рекомендация\n\n<b>Radiohead — OK Computer</b>\nжанр: Alternative; релиз: 1997\n\nТреки:\n• Paranoid Android\n• Karma Police\n• No Surprises", "media_url": None},
    ]
    random.shuffle(fallback)
    return fallback[:limit]

_FETCHERS: Dict[str, Callable[[int], List[Any]]] = {
    "jokes": fetch_anekdots,
    "news": fetch_news,
    "sport": fetch_sport,
    "games": fetch_games,
    "recipes": fetch_recipes,
    "memes": fetch_memes,
    "cats": fetch_cats,
    "music": fetch_music,
}


def _normalize_item(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        text = str(item.get("text") or "").strip()
        media_url = item.get("media_url") or None
        return {"text": text, "media_url": media_url}
    return {"text": str(item).strip(), "media_url": None}


def fetch_content_items(content_type: str, limit: int = 20) -> List[Dict[str, Any]]:
    normalized = normalize_content_type(content_type)
    raw_items = _FETCHERS[normalized](limit)
    result = [_normalize_item(item) for item in raw_items]
    return [item for item in result if item.get("text") or item.get("media_url")]


def fetch_content_item(content_type: str) -> Dict[str, Any]:
    items = fetch_content_items(content_type, limit=1)
    if not items:
        raise ContentSourceError(f"Источник {content_type_label(content_type)} не вернул контент")
    return items[0]
