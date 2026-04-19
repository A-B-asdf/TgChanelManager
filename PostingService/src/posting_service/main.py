from fastapi import FastAPI
from posting_service.api.routes import router

app = FastAPI(title="Posting Service", version="0.2.0")
app.include_router(router)