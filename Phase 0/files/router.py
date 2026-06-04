"""Aggregates all v1 endpoint routers.

Future phase routers (instruments, signals, trades, performance) get included
here as they are built.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()
api_router.include_router(health.router)
