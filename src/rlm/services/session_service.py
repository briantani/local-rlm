"""
Session Service for RLM.

Manages user sessions with API keys stored ONLY in memory.
API keys are never persisted to disk or database for security.

Phase 12: Core Library Refactoring
"""

import secrets
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock


@dataclass
class Session:
    """
    In-memory session with API keys.

    Security: API keys are stored only in memory and are never persisted.
    When the server restarts or session expires, keys must be re-entered.
    """
    session_id: str = field(default_factory=lambda: secrets.token_urlsafe(16))
    api_keys: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)

    def set_api_key(self, provider: str, key: str) -> None:
        """
        Set an API key for a provider.

        Args:
            provider: Provider name (e.g., "gemini", "openai", "ollama")
            key: The API key value
        """
        self.api_keys[provider.lower()] = key
        self.last_accessed = datetime.now()

    def get_api_key(self, provider: str) -> str | None:
        """
        Get an API key for a provider.

        Args:
            provider: Provider name (e.g., "gemini", "openai")

        Returns:
            The API key if set, None otherwise
        """
        self.last_accessed = datetime.now()
        return self.api_keys.get(provider.lower())

    def remove_api_key(self, provider: str) -> bool:
        """
        Remove an API key for a provider.

        Args:
            provider: Provider name

        Returns:
            True if key was removed, False if it didn't exist
        """
        provider = provider.lower()
        if provider in self.api_keys:
            del self.api_keys[provider]
            self.last_accessed = datetime.now()
            return True
        return False

    def has_required_keys(self, providers: list[str]) -> tuple[bool, list[str]]:
        """
        Check if session has all required API keys.

        Args:
            providers: List of provider names that require keys

        Returns:
            Tuple of (all_present, missing_providers)
        """
        self.last_accessed = datetime.now()
        missing = [p for p in providers if p.lower() not in self.api_keys]
        return len(missing) == 0, missing

    def get_configured_providers(self) -> list[str]:
        """
        Get list of providers with configured API keys.

        Returns:
            List of provider names
        """
        return list(self.api_keys.keys())

    def clear_all_keys(self) -> None:
        """Clear all API keys from the session."""
        self.api_keys.clear()
        self.last_accessed = datetime.now()


class SessionService:
    """
    Manages sessions in memory (no persistence).

    Thread-safe for use with FastAPI's async handlers and
    Python 3.14t's true parallelism.
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def create_session(self) -> Session:
        """
        Create a new session.

        Returns:
            A new Session instance with a unique ID
        """
        session = Session()
        with self._lock:
            self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        """
        Retrieve a session by ID.

        Args:
            session_id: The session ID to look up

        Returns:
            The Session if found, None otherwise
        """
        with self._lock:
            return self._sessions.get(session_id)

    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session and all its API keys.

        Args:
            session_id: The session ID to delete

        Returns:
            True if session was deleted, False if not found
        """
        with self._lock:
            if session_id in self._sessions:
                # Explicitly clear keys before deletion (defense in depth)
                self._sessions[session_id].clear_all_keys()
                del self._sessions[session_id]
                return True
            return False

    def set_api_key(self, session_id: str, provider: str, key: str) -> bool:
        """
        Set an API key for a session.

        Args:
            session_id: The session ID
            provider: Provider name (e.g., "gemini", "openai")
            key: The API key value

        Returns:
            True if key was set, False if session not found
        """
        session = self.get_session(session_id)
        if session:
            session.set_api_key(provider, key)
            return True
        return False

    def get_api_key(self, session_id: str, provider: str) -> str | None:
        """
        Get an API key from a session.

        Args:
            session_id: The session ID
            provider: Provider name

        Returns:
            The API key if found, None otherwise
        """
        session = self.get_session(session_id)
        if session:
            return session.get_api_key(provider)
        return None

    def get_session_count(self) -> int:
        """
        Get the number of active sessions.

        Returns:
            Number of sessions
        """
        with self._lock:
            return len(self._sessions)

    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> int:
        """
        Remove sessions older than max_age_hours.

        Args:
            max_age_hours: Maximum session age in hours

        Returns:
            Number of sessions removed
        """
        now = datetime.now()
        to_remove = []

        with self._lock:
            for session_id, session in self._sessions.items():
                age = now - session.last_accessed
                if age.total_seconds() > max_age_hours * 3600:
                    to_remove.append(session_id)

            for session_id in to_remove:
                self._sessions[session_id].clear_all_keys()
                del self._sessions[session_id]

        return len(to_remove)
