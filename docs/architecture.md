AI Stock Signal Pro - System Architecture



Version: 1.0



Status:



✅ Phase 0 Completed



✅ Phase 1 Completed



✅ Phase 2 Completed



⏳ Phase 3 In Progress



System Overview



AI Stock Signal Pro is a desktop-based quantitative analysis platform for Indian equity markets.



The platform is designed to generate explainable BUY and SELL signals using:



Technical Analysis

Fundamental Analysis

News Sentiment

Social Sentiment

Volatility Analysis

Risk Management



Supported Universe:



Nifty 50 Stocks

Bank Nifty Stocks

Nifty 50 Index

Bank Nifty Index

High-Level Architecture



┌──────────────────────────────────────────────┐

│ Desktop Client (Electron + React + TS) │

│ │

│ Dashboard │

│ Alerts │

│ Charts │

│ Signal Feed │

└─────────────────────┬────────────────────────┘

│

│ REST + WebSocket

│

┌─────────────────────▼────────────────────────┐

│ FastAPI Backend │

│ │

│ API Gateway │

│ Authentication │

│ Validation │

│ Orchestration │

└───────┬───────────┬───────────┬──────────────┘

│ │ │

▼ ▼ ▼



Ingestion Analysis Scoring



&#x20;   │

&#x20;   ▼



Signal Engine



&#x20;   │

&#x20;   ▼



Risk Engine



&#x20;   │

&#x20;   ▼



Persistence



&#x20;   │

&#x20;   ▼



PostgreSQL + Redis



Core Modules

Ingestion



Responsibilities:



Broker integration

Historical data ingestion

Instrument synchronization

News ingestion

Social data ingestion

Fundamental data ingestion



Current Status:



Completed:



Zerodha integration

Historical OHLCV sync

Technical Analysis



Responsibilities:



Indicator calculations

Trend detection

Technical scoring



Indicators:



RSI

MACD

EMA20

EMA50

EMA200

VWAP

ATR

ADX

Bollinger Bands

SuperTrend

Volume Analysis

Support \& Resistance



Current Status:



Completed



Fundamental Analysis



Responsibilities:



PE analysis

ROE analysis

ROCE analysis

Earnings analysis

Sector-relative scoring



Status:



Planned



Sentiment Analysis



Responsibilities:



News sentiment

Social sentiment

Event extraction

Catalyst detection



Models:



FinBERT

OpenAI



Status:



Planned



Volatility Analysis



Responsibilities:



ATR

Historical volatility

Beta analysis

Market regime classification



Status:



Planned



Fusion Scoring Engine



Responsibilities:



Combine:



Technical Score

Fundamental Score

News Score

Social Score

Volatility Score



Formula:



Composite Score =

Σ(weight × score × confidence)



Weights are versioned and stored in config\_weights.



Status:



Next Phase



Signal Engine



Responsibilities:



Generate:



STRONG\_BUY

BUY

HOLD

SELL

STRONG\_SELL



Signal generation must be deterministic and reproducible.



Status:



Next Phase



Risk Management Engine



Responsibilities:



Entry Price

Stop Loss

Target Price

Position Sizing

Risk Validation



Minimum Risk Reward:



1:2



Status:



Planned



Backtesting Architecture



Execution Modes:



LIVE

BACKTEST



Core Components:



Clock



Implementations:



LiveClock

SimulatedClock



Purpose:



Provide deterministic time control.



DataFeed



Purpose:



Provide point-in-time access to market data.



Requirement:



No future data access.



All analysis must respect:



data\_timestamp <= clock.now()



This guarantees no look-ahead bias.



Backtest Runs



Stored in:



backtest\_runs



Tracks:



Parameters

Date ranges

Weights version

Metrics

Status

Data Flow

Scheduler triggers jobs.

Workers ingest:

OHLCV

Fundamentals

News

Social data

Data stored in PostgreSQL.

Analysis engines generate scores.

Fusion engine creates composite score.

Signal engine classifies signal.

Risk engine computes:

Entry

Stop-loss

Target

Signals stored.

Alerts published via Redis Pub/Sub.

Desktop application receives updates.

Design Principles

Strategy Pattern



Used for:



Indicators

Broker adapters

Scoring modules

Adapter Pattern



Used for:



Zerodha

Upstox

Angel One

Repository Pattern



Used for:



Data access isolation

Testing

Event-Driven Processing



Redis:



Pub/Sub

Task Queue

Scalability



Backend:



Stateless FastAPI services



Workers:



Horizontally scalable



Database:



PostgreSQL

Future TimescaleDB support



Cache:



Redis



Desktop:



Thin client architecture

AI Usage Policy



OpenAI is used for:



News summarization

Event extraction

Human-readable rationale generation



OpenAI must NOT:



Directly generate buy/sell signals

Determine entry or exit prices

Override deterministic scoring logic



All trading decisions must remain explainable and reproducible.



Implementation Roadmap



Completed:



Phase 0

Phase 1

Phase 2



Current:



Phase 3 Fusion Scoring Engine



Future:



Risk Management

Sentiment Analysis

Fundamental Analysis

Desktop UI

Trade Analytics

Performance Tracking

Production Hardening



This document is the authoritative architectural reference for the project.

