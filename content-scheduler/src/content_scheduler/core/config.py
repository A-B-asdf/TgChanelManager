import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    DB_PATH = os.getenv("SCHEDULER_DB_PATH", "/app/data/scheduler.db")
    POSTING_SERVICE_URL = os.getenv("POSTING_SERVICE_URL", "http://localhost:8001")
    FULFILLMENT_SERVICE_URL = os.getenv("FULFILLMENT_SERVICE_URL", "http://localhost:8003")
