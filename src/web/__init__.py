"""
RLM Web Application package.

Avoid importing `create_app` at package import time to prevent heavy
side-effects (template loading, optional dependencies like weasyprint)
when other modules import submodules such as `src.web.task_runner`.

Import `create_app` explicitly where needed: `from src.web.app import create_app`.
"""

__all__ = []
