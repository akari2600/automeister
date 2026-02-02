"""Logging system for Automeister."""

import logging
import os
import re
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Patterns for sensitive data masking
SENSITIVE_PATTERNS = [
    (
        re.compile(
            r'(password|passwd|pwd|secret|token|api_key|apikey)'
            r'(["\']?\s*[:=]\s*["\']?)([^\s"\']+)',
            re.IGNORECASE,
        ),
        r'\1\2***',
    ),
    (re.compile(r'(Bearer|Basic)\s+\S+', re.IGNORECASE), r'\1 ***'),
]


class SensitiveDataFilter(logging.Filter):
    """Filter that masks sensitive data in log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Mask sensitive data in the log message."""
        if isinstance(record.msg, str):
            record.msg = mask_sensitive_data(record.msg)
        if record.args:
            record.args = tuple(
                mask_sensitive_data(str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


def mask_sensitive_data(text: str) -> str:
    """Mask sensitive data in a string."""
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def get_log_dir() -> Path:
    """Get the log directory path."""
    config_home = os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config"))
    log_dir = Path(config_home) / "automeister" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = False,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 3,
) -> logging.Logger:
    """
    Set up the logging system.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR).
        log_to_file: Whether to log to file.
        log_to_console: Whether to log to console.
        max_bytes: Maximum size of each log file.
        backup_count: Number of backup files to keep.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("automeister")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()

    if log_to_file:
        log_dir = get_log_dir()
        log_file = log_dir / f"automeister_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        logger.addHandler(file_handler)

    if log_to_console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Optional name for sub-logger (e.g., 'macro', 'actions').

    Returns:
        Logger instance.
    """
    if name:
        return logging.getLogger(f"automeister.{name}")
    return logging.getLogger("automeister")


# Initialize default logger
_logger: logging.Logger | None = None


def init_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_to_console: bool = False,
) -> logging.Logger:
    """Initialize the global logger."""
    global _logger
    _logger = setup_logging(
        level=level,
        log_to_file=log_to_file,
        log_to_console=log_to_console,
    )
    return _logger


def log_debug(message: str, *args: object) -> None:
    """Log a debug message."""
    logger = _logger or get_logger()
    logger.debug(message, *args)


def log_info(message: str, *args: object) -> None:
    """Log an info message."""
    logger = _logger or get_logger()
    logger.info(message, *args)


def log_warning(message: str, *args: object) -> None:
    """Log a warning message."""
    logger = _logger or get_logger()
    logger.warning(message, *args)


def log_error(message: str, *args: object) -> None:
    """Log an error message."""
    logger = _logger or get_logger()
    logger.error(message, *args)


def log_exception(message: str, *args: object) -> None:
    """Log an exception with traceback."""
    logger = _logger or get_logger()
    logger.exception(message, *args)


def clean_old_logs(days: int = 30) -> int:
    """
    Remove log files older than specified days.

    Args:
        days: Number of days to keep logs.

    Returns:
        Number of files removed.
    """
    log_dir = get_log_dir()
    cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
    removed = 0

    for log_file in log_dir.glob("automeister_*.log*"):
        if log_file.stat().st_mtime < cutoff:
            log_file.unlink()
            removed += 1

    return removed
