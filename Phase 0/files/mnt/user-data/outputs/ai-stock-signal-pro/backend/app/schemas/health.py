"""Pydantic schemas for health/readiness responses."""
from pydantic import BaseModel


class ComponentHealth(BaseModel):
    database: bool
    redis: bool


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    environment: str
    version: str
    components: ComponentHealth
