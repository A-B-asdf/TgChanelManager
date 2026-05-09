import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    DB_PATH = os.getenv("FULFILLMENT_DB_PATH", "/app/data/fulfillment.db")
    CHANNEL_SERVICE_URL = os.getenv("CHANNEL_SERVICE_URL", "http://localhost:8004")
    CONTENT_SCHEDULER_URL = os.getenv("CONTENT_SCHEDULER_URL", "http://localhost:8000")
