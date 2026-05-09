from fastapi import FastAPI
from tg_adapter_posting.api.routes import router

app = FastAPI(title="TgAdapter Posting Service")
app.include_router(router)
