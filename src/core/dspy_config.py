"""
Centralized DSPy Configuration.

Handles global settings for DSPy, specifically caching.
This ensures consistent behavior across CLI and Web interfaces.
"""

import os
import dspy
from pathlib import Path
from src.core.logger import logger

def configure_dspy(cache_enabled: bool = True, project_root: Path | None = None) -> None:
    """
    Configure global DSPy settings.

    Args:
        cache_enabled: Whether to enable caching (default: True)
        project_root: Optional path to project root. If None, detected automatically.
    """
    if not project_root:
        # Detect project root (3 levels up from this file)
        project_root = Path(__file__).resolve().parent.parent.parent

    # Configure caching
    if cache_enabled:
        # Use a local .dspy_cache directory in the project root
        cache_dir = project_root / ".dspy_cache"
        
        # Create directory if it doesn't exist
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Set environment variables that DSPy respects
        os.environ["DSP_CACHEDIR"] = str(cache_dir)
        os.environ["DSP_CACHEBOOL"] = "True"
        
        # Also configure via dspy.settings for good measure (works in newer versions)
        # Note: dspy.settings.configure might be required depending on version
        try:
            dspy.settings.configure(lm=dspy.settings.lm, rm=dspy.settings.rm, cache=True)
            logger.debug(f"DSPy caching enabled at {cache_dir}")
        except Exception as e:
            logger.warning(f"Could not configure dspy.settings: {e}")
            
    else:
        os.environ["DSP_CACHEBOOL"] = "False"
        try:
            dspy.settings.configure(lm=dspy.settings.lm, rm=dspy.settings.rm, cache=False)
            logger.debug("DSPy caching disabled")
        except Exception:
            pass
