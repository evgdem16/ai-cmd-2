"""Sets up file-based logging for the application."""

import logging
import os


def setup_logger(log_file: str = "logs/app.log", level: str = "INFO") -> logging.Logger:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    numeric_level = getattr(logging, level.upper(), logging.INFO)

    logger = logging.getLogger("lm_chat")
    logger.setLevel(numeric_level)

    if not logger.handlers:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(numeric_level)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(module)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger("lm_chat")
