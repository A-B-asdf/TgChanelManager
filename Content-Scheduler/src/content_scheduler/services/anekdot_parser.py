import requests
from bs4 import BeautifulSoup

def fetch_anekdot() -> str:
    url = "https://www.anekdot.ru/last/anekdot/"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        # Примерный селектор (нужно уточнить по реальной структуре)
        anekdot_block = soup.find("div", class_="text")
        if anekdot_block:
            return anekdot_block.get_text(strip=True)
        return "Анекдот не найден"
    except Exception as e:
        return f"Ошибка загрузки анекдота: {e}"