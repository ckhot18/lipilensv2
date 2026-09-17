"""Central logging configuration for LipiLens.

Import once at application startup (e.g. in backend/main.py or scripts),
then use `logger = logging.getLogger(__name__)` in every other module.
"""

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a consistent format (idempotent)."""
    if logging.getLogger().handlers:
        # Already configured — don't add duplicate handlers.
        return
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger."""
    return logging.getLogger(name)
