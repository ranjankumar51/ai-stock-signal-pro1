"""Logging architecture.

Uses structlog over the stdlib logging backbone so that:
  * development gets readable, colorized console output,
  * production emits single-line JSON (easy to ship to Loki/ELK/CloudWatch),
  * uvicorn / sqlalchemy logs are routed through the same pipeline.

Call `configure_logging()` once at process startup. Obtain loggers with
`structlog.get_logger(__name__)` anywhere thereafter.
"""
import logging
import sys

import structlog

from app.core.config import settings


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Shared processors run for every event.
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
    ]

    if settings.log_json:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=shared_processors
        + [structlog.processors.format_exc_info, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging (uvicorn, sqlalchemy, alembic) into structlog.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_StdlibFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for noisy in ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).handlers = [handler]
        logging.getLogger(noisy).propagate = False


class _StdlibFormatter(logging.Formatter):
    """Render stdlib LogRecords through structlog's renderer for consistency."""

    def format(self, record: logging.LogRecord) -> str:
        logger = structlog.get_logger(record.name)
        return f"{record.name} | {record.getMessage()}"


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)
