import logging

import structlog


def _renderer(log_format: str) -> structlog.types.Processor:
    """Select the appropriate renderer based on the configured format."""

    if log_format.lower() == "json":
        return structlog.processors.JSONRenderer()
    return structlog.dev.ConsoleRenderer()


def setup_logging(log_level: str = "INFO", log_format: str = "pretty") -> None:
    """Configure application-wide logging for both development and production."""

    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        format="%(message)s",
        level=level,
        handlers=[logging.StreamHandler()],
    )

    renderer = _renderer(log_format)
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )
