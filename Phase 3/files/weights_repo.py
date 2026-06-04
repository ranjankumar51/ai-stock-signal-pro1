"""Data access for versioned fusion weights (config_weights)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scoring import ConfigWeights


class WeightsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active(self) -> ConfigWeights | None:
        """Return the single active weight set, or None if unconfigured."""
        res = await self.session.execute(
            select(ConfigWeights).where(ConfigWeights.is_active.is_(True)).limit(1)
        )
        return res.scalar_one_or_none()
