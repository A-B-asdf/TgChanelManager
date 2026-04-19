import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_PATH = os.getenv("POSTING_DB_PATH", "/app/data/posting.db")
    TG_ADAPTER_URL = os.getenv("TG_ADAPTER_URL", "http://localhost:9000")