from fastapi import FastAPI
from posting_service.api.routes import router

app = FastAPI(title="Posting Service")
app.include_router(router)
