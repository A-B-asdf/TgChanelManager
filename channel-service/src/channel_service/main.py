from fastapi import FastAPI
from channel_service.api.routes import router

app = FastAPI(title="Channel Service")
app.include_router(router)
