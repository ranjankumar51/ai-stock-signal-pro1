"""Aggregates all v1 endpoint routers.

Future phase routers (trades, performance) get included here as they are built.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import health, ingestion, market_data, signals

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(ingestion.router)
api_router.include_router(market_data.router)
api_router.include_router(signals.router)
