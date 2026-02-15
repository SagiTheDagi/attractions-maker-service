"""
Logging configuration using loguru.
"""
import sys
from loguru import logger
from config.settings import LOG_LEVEL, LOG_FORMAT, LOG_FILE, LOG_ROTATION, LOG_RETENTION, LOGS_DIR


def setup_logger():
    """Configure the logger with file and console output."""
    # Ensure logs directory exists
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Remove default logger
    logger.remove()

    # Add console logger
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        colorize=True,
    )

    # Add file logger
    logger.add(
        LOG_FILE,
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        encoding="utf-8",
    )

    logger.info("Logger initialized")
    return logger


# Create singleton logger instance
log = setup_logger()
