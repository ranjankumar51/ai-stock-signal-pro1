"""Signal endpoints.

Generation is synchronous and broker-free: the fusion + risk engines read only
from PostgreSQL (price_data via the point-in-time DataFeed), so no job queue is
needed here. LIVE mode only — backtest generation is driven by the (future)
backtest runner through the same service.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.ingestion.intervals import parse_timeframe
from app.models.enums import ExecutionMode
from app.repositories.instrument_repo import InstrumentRepository
from app.repositories.signal_repo import SignalRepository
from app.schemas.signals import GenerateSignalRequest, SignalResponse
from app.services.signal_generation import SignalGenerationService

router = APIRouter(prefix="/signals", tags=["signals"])


def _f(x) -> float | None:
    return None if x is None else float(x)


async def _resolve_instrument(db: AsyncSession, symbol: str):
    inst = await InstrumentRepository(db).get_by_symbol(symbol)
    if inst is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown symbol: {symbol}")
    return inst


@router.post("/generate", response_model=SignalResponse, status_code=status.HTTP_201_CREATED)
async def generate_signal(
    body: GenerateSignalRequest,
    db: AsyncSession = Depends(get_db),
) -> SignalResponse:
    try:
        tf = parse_timeframe(body.tf)
    except (ValueError, KeyError):
        raise HTTPException(status_code=422, detail=f"Invalid timeframe: {body.tf}")
    inst = await _resolve_instrument(db, body.symbol)
    gen = await SignalGenerationService(db).generate(inst.id, tf)
    return SignalResponse(
        instrument_id=inst.id,
        symbol=inst.symbol,
        tf=tf.value,
        ts=gen.as_of.isoformat(),
        signal=gen.classification.signal.value,
        composite_score=round(gen.fusion.composite, 4),
        score_0_100=gen.fusion.score_0_100,
        confidence=round(gen.fusion.confidence, 4),
        side=gen.classification.side.value if gen.classification.side else None,
        status=gen.status.value,
        entry=_f(gen.entry),
        stop_loss=_f(gen.stop_loss),
        target=_f(gen.target),
        risk_reward=_f(gen.risk_reward),
        position_size=_f(gen.position_size),
        risk_confidence=_f(gen.risk_confidence),
        weights_version=gen.fusion.weights_version,
        snapshot_id=gen.snapshot_id,
        rationale=gen.rationale,
        mode=gen.mode.value,
    )


@router.get("/{symbol}/latest", response_model=SignalResponse)
async def latest_signal(
    symbol: str,
    tf: str = Query(default="1d", examples=["1m", "5m", "15m", "1h", "1d"]),
    db: AsyncSession = Depends(get_db),
) -> SignalResponse:
    try:
        timeframe = parse_timeframe(tf)
    except (ValueError, KeyError):
        raise HTTPException(status_code=422, detail=f"Invalid timeframe: {tf}")
    inst = await _resolve_instrument(db, symbol)
    row = await SignalRepository(db).get_latest(inst.id, timeframe, ExecutionMode.LIVE)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No signal for {symbol} @ {tf}",
        )
    rationale = row.rationale or {}
    return SignalResponse(
        instrument_id=inst.id,
        symbol=inst.symbol,
        tf=timeframe.value,
        ts=row.ts.isoformat(),
        signal=row.signal.value,
        composite_score=float(row.composite_score),
        score_0_100=rationale.get("score_0_100", round((float(row.composite_score) + 1.0) * 50.0, 2)),
        confidence=float(row.confidence),
        side=row.side.value if row.side else None,
        status=row.status.value,
        entry=_f(row.entry),
        stop_loss=_f(row.stop_loss),
        target=_f(row.target),
        risk_reward=_f(row.risk_reward),
        position_size=_f(row.position_size),
        risk_confidence=_f(row.risk_confidence),
        weights_version=rationale.get("weights_version"),
        snapshot_id=row.snapshot_id,
        rationale=rationale,
        mode=row.mode.value,
    )
