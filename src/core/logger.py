import logging
import os
import sys
from datetime import datetime
from pathlib import Path


class LazyLogger:
    """
    A lazy logger wrapper that defers file handler creation until first use.
    This prevents log files from being created on module import during testing.
    """

    def __init__(self, name: str = "RLM", log_level: int = logging.DEBUG):
        self._name = name
        self._log_level = log_level
        self._logger: logging.Logger | None = None
        self._initialized = False

    def _get_logger(self) -> logging.Logger:
        """Initialize the logger on first access."""
        if self._logger is not None:
            return self._logger

        self._logger = logging.getLogger(self._name)
        self._logger.setLevel(self._log_level)

        # Avoid adding handlers multiple times
        if self._logger.handlers:
            return self._logger

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console Handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self._log_level)
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)

        # File Handler (skip during testing)
        if not os.environ.get("RLM_TESTING"):
            try:
                current_path = Path(__file__).resolve()
                project_root = current_path.parent.parent.parent
                if (project_root / "pyproject.toml").exists():
                    log_dir = project_root / "logs"
                else:
                    log_dir = Path("logs")
            except Exception:
                log_dir = Path("logs")

            log_dir.mkdir(exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"rlm_run_{timestamp}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(self._log_level)
            file_handler.setFormatter(formatter)
            self._logger.addHandler(file_handler)

        self._initialized = True
        return self._logger

    def debug(self, msg: str, *args, **kwargs):
        self._get_logger().debug(msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        self._get_logger().info(msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        self._get_logger().warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        self._get_logger().error(msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        self._get_logger().critical(msg, *args, **kwargs)


def setup_logger(name: str = "RLM", log_level: int = logging.DEBUG, log_to_file: bool = True) -> logging.Logger:
    """
    Configures and returns a logger with console and file handlers.

    DEPRECATED: Use the `logger` singleton instead for lazy initialization.

    Args:
        name: The name of the logger.
        log_level: The logging level (default: DEBUG).
        log_to_file: Whether to write logs to a file (default: True).

    Returns:
        A configured logging.Logger instance.
    """
    _logger = logging.getLogger(name)
    _logger.setLevel(log_level)

    # Avoid adding handlers multiple times if the logger is already configured
    if _logger.handlers:
        return _logger

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)

    # File Handler
    if log_to_file and not os.environ.get("RLM_TESTING"):
        try:
            current_path = Path(__file__).resolve()
            project_root = current_path.parent.parent.parent
            if (project_root / "pyproject.toml").exists():
                log_dir = project_root / "logs"
            else:
                log_dir = Path("logs")
        except Exception:
            log_dir = Path("logs")

        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"rlm_run_{timestamp}.log"

        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)

    return _logger


# Create a lazy logger instance for easy import
# This prevents file creation until the logger is actually used
logger = LazyLogger()
