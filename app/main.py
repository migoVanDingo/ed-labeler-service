from fastapi import FastAPI

from app.api.controller.health_check import router as health_router
from app.api.controller.labeling import router as labeling_router

app = FastAPI(title="Core Service")

# REST endpoints
app.include_router(health_router, prefix="/health", tags=["Health"])
app.include_router(labeling_router, tags=["Labeling"])
