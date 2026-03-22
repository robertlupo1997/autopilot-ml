"""Logging configuration for mlforge.

Sets up structured logging with a file handler (for overnight debugging)
and a console handler (for immediate feedback). Rich LiveProgress handles
terminal UI separately -- this module handles audit-trail logging.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(
    log_dir: Path | None = None,
    verbose: bool = False,
) -> None:
    """Configure the ``mlforge`` logger with console and optional file handlers.

    Args:
        log_dir: Directory for the log file. If provided, creates a
            ``RotatingFileHandler`` writing to ``log_dir/mlforge.log``.
        verbose: If True, set console handler to DEBUG; otherwise WARNING.
    """
    logger = logging.getLogger("mlforge")
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Console handler -- add once, update level on subsequent calls
    has_console = any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler) for h in logger.handlers)
    if not has_console:
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG if verbose else logging.WARNING)
        console.setFormatter(fmt)
        logger.addHandler(console)

    # File handler -- add once when log_dir is provided
    has_file = any(isinstance(h, RotatingFileHandler) for h in logger.handlers)
    if log_dir is not None and not has_file:
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            log_dir / "mlforge.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=3,
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        logger.addHandler(fh)
