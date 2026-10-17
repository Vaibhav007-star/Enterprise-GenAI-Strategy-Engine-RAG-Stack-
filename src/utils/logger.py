import logging
import sys
from typing import Optional


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """Return a configured logger with clean formatting."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
    log_level = getattr(logging, (level or "INFO").upper(), logging.INFO)
    logger.setLevel(log_level)
    return logger
