"""
Centralized loader for compiled DSPy modules.

This module provides a single source of truth for discovering and loading
optimized/compiled DSPy module artifacts.
"""
from pathlib import Path
from typing import TypeVar

import dspy

from src.core.logger import logger

T = TypeVar("T", bound=dspy.Module)

# Default paths for compiled modules (relative to project root)
COMPILED_MODULES = {
    "architect": "src/modules/compiled_architect.json",
    "coder": "src/modules/coder_compiled.json",
}


def get_project_root() -> Path:
    """Find the project root by looking for pyproject.toml."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    return Path.cwd()


def get_compiled_path(module_name: str) -> Path | None:
    """
    Get the path to a compiled module if it exists.

    Args:
        module_name: The name of the module (e.g., "architect", "coder").

    Returns:
        Path to the compiled JSON file, or None if not found.
    """
    if module_name not in COMPILED_MODULES:
        return None

    project_root = get_project_root()
    compiled_path = project_root / COMPILED_MODULES[module_name]

    if compiled_path.exists():
        return compiled_path
    return None


def load_compiled_module(module: T, module_name: str) -> T:
    """
    Load compiled weights into a DSPy module if available.

    Args:
        module: The DSPy module instance to load weights into.
        module_name: The name of the module (e.g., "architect", "coder").

    Returns:
        The same module instance (potentially with loaded weights).
    """
    compiled_path = get_compiled_path(module_name)

    if compiled_path:
        try:
            module.load(str(compiled_path))
            logger.debug(f"Loaded compiled {module_name} from {compiled_path}")
        except Exception as e:
            logger.warning(f"Failed to load compiled {module_name}: {e}")

    return module


def list_available_compiled_modules() -> list[str]:
    """
    List all compiled modules that are currently available.

    Returns:
        List of module names with existing compiled artifacts.
    """
    available = []
    for name in COMPILED_MODULES:
        if get_compiled_path(name):
            available.append(name)
    return available
