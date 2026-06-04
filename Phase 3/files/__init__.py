"""Score-provider registry + default fusion weights.

Add a real fundamental/news/social/volatility engine later by replacing the
matching placeholder here — no caller changes. ``technical`` is passed in
because it needs the Phase 2 engine (Clock + DataFeed), which the orchestration
layer owns.
"""
from __future__ import annotations

from app.fusion.dimensions import ScoreProvider
from app.fusion.providers.fundamental import FundamentalScoreProvider
from app.fusion.providers.news import NewsScoreProvider
from app.fusion.providers.social import SocialScoreProvider
from app.fusion.providers.technical import TechnicalScoreProvider
from app.fusion.providers.volatility import VolatilityScoreProvider

# Fallback weights when no active config_weights row exists. Placeholder
# dimensions still carry intended weight; they are simply skipped while
# unavailable, so today the composite equals the technical score.
DEFAULT_FUSION_WEIGHTS: dict[str, float] = {
    "technical": 0.40,
    "fundamental": 0.20,
    "news": 0.15,
    "social": 0.10,
    "volatility": 0.15,
}


def default_providers(technical: TechnicalScoreProvider) -> list[ScoreProvider]:
    return [
        technical,
        FundamentalScoreProvider(),
        NewsScoreProvider(),
        SocialScoreProvider(),
        VolatilityScoreProvider(),
    ]
