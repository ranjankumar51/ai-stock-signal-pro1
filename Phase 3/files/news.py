"""News dimension — Phase 3 plug-in placeholder.

Implements the ScoreProvider contract but reports ``available=False`` so it is
excluded from the fuse. Replace with the real news engine in a later phase; no
other code changes are required.
"""
from __future__ import annotations

from app.fusion.dimensions import (
    Dimension,
    DimensionScore,
    ProviderContext,
    ScoreProvider,
)


class NewsScoreProvider(ScoreProvider):
    dimension = Dimension.NEWS

    async def score(self, ctx: ProviderContext) -> DimensionScore:
        return self._unavailable()
