import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    DB_PATH = os.getenv("CHANNEL_DB_PATH", "/app/data/channel.db")
    TG_ADAPTER_CHANNEL_URL = os.getenv("TG_ADAPTER_CHANNEL_URL", "http://localhost:8006")
