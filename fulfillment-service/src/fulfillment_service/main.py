from fastapi import FastAPI
from fulfillment_service.api.routes import router

app = FastAPI(title="Fulfillment Service")
app.include_router(router)
