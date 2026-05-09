from typing import Optional

import requests
from bs4 import BeautifulSoup


def fetch_anekdot() -> str:
    url = "https://www.anekdot.ru/last/anekdot/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "lxml")
    anekdot_block = soup.find("div", class_="text")
    if not anekdot_block:
        raise RuntimeError("Анекдот не найден на странице")
    text = anekdot_block.get_text("\n", strip=True)
    if not text:
        raise RuntimeError("Анекдот найден, но текст пустой")
    return text
