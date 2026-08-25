"""FastAPI app exposing the APIx dataset (requirement #8: an API NSO/RBI can
consume). Run with: uvicorn api.main:app --reload
Interactive docs at /docs (OpenAPI) once running.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import elasticity_router, fares_router, heatmap_router, index_router, routes_router, validation_router
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="APIx -- Real-time Airfare Price Index API",
    description="Daily/weekly/monthly airfare price index for a DGCA-weighted city-pair basket, "
    "built from scraped/synthetic airline and OTA fare observations.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["health"])
def health():
    return {"status": "ok"}


app.include_router(index_router.router)
app.include_router(routes_router.router)
app.include_router(fares_router.router)
app.include_router(heatmap_router.router)
app.include_router(elasticity_router.router)
app.include_router(validation_router.router)
