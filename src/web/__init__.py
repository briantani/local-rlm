"""
RLM Web Application.

FastAPI backend for the RLM Agent with REST APIs and WebSocket streaming.
Phase 13: FastAPI Backend with WebSocket Streaming.
"""

from src.web.app import create_app

__all__ = ["create_app"]
