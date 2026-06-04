"""News and social sentiment storage tables.

Phase 0 defines only the tables. The ingestion/FinBERT engines that populate
``sentiment_score`` and ``summary`` are out of scope until later phases.
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import SentimentLabel, sentiment_label_enum


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (
        CheckConstraint(
            "sentiment_score IS NULL OR sentiment_score BETWEEN -1 AND 1",
            name="news_sentiment_range",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instrument_id: Mapped[int | None] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE")
    )
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str | None] = mapped_column(String(1024))
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    sentiment_label: Mapped[SentimentLabel | None] = mapped_column(sentiment_label_enum)
    summary: Mapped[str | None] = mapped_column(Text)
    ingested_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SocialItem(Base):
    __tablename__ = "social_items"
    __table_args__ = (
        UniqueConstraint(
            "instrument_id", "platform", "window_ts", name="uq_social_bucket"
        ),
        CheckConstraint(
            "sentiment_score IS NULL OR sentiment_score BETWEEN -1 AND 1",
            name="social_sentiment_range",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instrument_id: Mapped[int] = mapped_column(
        ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String(32), nullable=False)
    window_ts: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    sentiment_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    mention_volume: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    ingested_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
