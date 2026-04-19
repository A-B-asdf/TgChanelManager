import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DB_PATH = os.getenv("SCHEDULER_DB_PATH", "/app/data/scheduler.db")
    POSTING_SERVICE_URL = os.getenv("POSTING_SERVICE_URL", "http://localhost:8001")
    CRON_SCHEDULE = os.getenv("CRON_SCHEDULE", "0 12,0 * * *")
    TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")