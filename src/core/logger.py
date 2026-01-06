import logging
import sys
from datetime import datetime
from pathlib import Path

def setup_logger(name: str = "RLM", log_level: int = logging.DEBUG, log_to_file: bool = True) -> logging.Logger:
    """
    Configures and returns a logger with console and file handlers.

    Args:
        name: The name of the logger.
        log_level: The logging level (default: DEBUG).
        log_to_file: Whether to write logs to a file (default: True).

    Returns:
        A configured logging.Logger instance.
    """
    logger = logging.getLogger(name)
    logger.setLevel(log_level)

    # Avoid adding handlers multiple times if the logger is already configured
    if logger.handlers:
        return logger

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    if log_to_file:
        # Determine log directory relative to the project root, or cwd
        # We try to find the project root by looking for pyproject.toml up the tree
        # or defaults to cwd/logs

        try:
             # Basic logical project root detection
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
        logger.addHandler(file_handler)

        # Log the start of the session
        # Use simple print for this one check to confirm logging system status if needed
        # but relying on the logger itself is better.

    return logger

# Create a default logger instance for easy import
# Note: Users can re-configure it if they want different names, but this singleton is convenient.
logger = setup_logger()
