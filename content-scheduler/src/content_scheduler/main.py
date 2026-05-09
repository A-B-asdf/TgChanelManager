from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from content_scheduler.api.routes import router
from content_scheduler.services.scheduler_service import restore_active_schedules

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    restored = restore_active_schedules()
    logging.getLogger(__name__).info("Restored %s active schedules", restored)
    yield


app = FastAPI(title="Content-Scheduler Service", lifespan=lifespan)
app.include_router(router)
