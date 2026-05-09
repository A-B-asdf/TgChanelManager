from fastapi import FastAPI
from tg_adapter_channel.api.routes import router

app = FastAPI(title="TgAdapter Channel Service")
app.include_router(router)
