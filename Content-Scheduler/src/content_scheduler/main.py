from fastapi import FastAPI
from content_scheduler.api.routes import router

app = FastAPI(title="Content-Scheduler Service", version="0.2.0")
app.include_router(router)