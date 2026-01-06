"""
Tests for the RLM Service Layer.

Phase 12: Core Library Refactoring
"""

import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.rlm.services.session_service import Session, SessionService
from src.rlm.services.config_service import ConfigService, ProfileSummary, ValidationResult


# =============================================================================
# Session Tests
# =============================================================================


class TestSession:
    """Tests for the Session dataclass."""

    def test_session_creation(self):
        """Test that sessions are created with unique IDs."""
        session1 = Session()
        session2 = Session()

        assert session1.session_id != session2.session_id
        assert len(session1.session_id) > 10  # Reasonably long token
        assert session1.api_keys == {}
        assert isinstance(session1.created_at, datetime)

    def test_set_and_get_api_key(self):
        """Test setting and getting API keys."""
        session = Session()

        session.set_api_key("gemini", "test-gemini-key")
        session.set_api_key("OpenAI", "test-openai-key")  # Test case insensitivity

        assert session.get_api_key("gemini") == "test-gemini-key"
        assert session.get_api_key("GEMINI") == "test-gemini-key"  # Case insensitive get
        assert session.get_api_key("openai") == "test-openai-key"
        assert session.get_api_key("anthropic") is None

    def test_remove_api_key(self):
        """Test removing API keys."""
        session = Session()
        session.set_api_key("gemini", "test-key")

        assert session.remove_api_key("gemini") is True
        assert session.get_api_key("gemini") is None
        assert session.remove_api_key("gemini") is False  # Already removed

    def test_has_required_keys(self):
        """Test checking for required keys."""
        session = Session()
        session.set_api_key("gemini", "key1")
        session.set_api_key("openai", "key2")

        has_all, missing = session.has_required_keys(["gemini", "openai"])
        assert has_all is True
        assert missing == []

        has_all, missing = session.has_required_keys(["gemini", "anthropic"])
        assert has_all is False
        assert missing == ["anthropic"]

    def test_get_configured_providers(self):
        """Test getting list of configured providers."""
        session = Session()
        session.set_api_key("gemini", "key1")
        session.set_api_key("openai", "key2")

        providers = session.get_configured_providers()
        assert set(providers) == {"gemini", "openai"}

    def test_clear_all_keys(self):
        """Test clearing all API keys."""
        session = Session()
        session.set_api_key("gemini", "key1")
        session.set_api_key("openai", "key2")

        session.clear_all_keys()

        assert session.api_keys == {}
        assert session.get_api_key("gemini") is None


class TestSessionService:
    """Tests for the SessionService."""

    def test_create_session(self):
        """Test creating sessions."""
        service = SessionService()

        session = service.create_session()

        assert session is not None
        assert len(session.session_id) > 0
        assert service.get_session_count() == 1

    def test_get_session(self):
        """Test retrieving sessions by ID."""
        service = SessionService()
        session = service.create_session()

        retrieved = service.get_session(session.session_id)

        assert retrieved is session
        assert service.get_session("nonexistent") is None

    def test_delete_session(self):
        """Test deleting sessions clears API keys."""
        service = SessionService()
        session = service.create_session()
        session.set_api_key("gemini", "secret-key")
        session_id = session.session_id

        result = service.delete_session(session_id)

        assert result is True
        assert service.get_session(session_id) is None
        assert service.delete_session(session_id) is False  # Already deleted
        # Verify keys are cleared (session object still exists locally but keys are empty)
        assert session.api_keys == {}

    def test_set_api_key_via_service(self):
        """Test setting API keys through the service."""
        service = SessionService()
        session = service.create_session()

        result = service.set_api_key(session.session_id, "gemini", "test-key")

        assert result is True
        assert service.get_api_key(session.session_id, "gemini") == "test-key"

        # Test with non-existent session
        assert service.set_api_key("fake-id", "gemini", "key") is False
        assert service.get_api_key("fake-id", "gemini") is None

    def test_thread_safety(self):
        """Test that SessionService is thread-safe."""
        import threading

        service = SessionService()
        sessions_created = []
        errors = []

        def create_sessions():
            try:
                for _ in range(10):
                    session = service.create_session()
                    sessions_created.append(session.session_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=create_sessions) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert service.get_session_count() == 50
        # All session IDs should be unique
        assert len(set(sessions_created)) == 50

    def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions."""
        service = SessionService()

        # Create sessions
        old_session = service.create_session()
        old_session.set_api_key("gemini", "old-key")
        new_session = service.create_session()
        new_session.set_api_key("gemini", "new-key")

        # Manually age the old session
        old_session.last_accessed = datetime.now() - timedelta(hours=25)

        # Cleanup sessions older than 24 hours
        removed = service.cleanup_expired_sessions(max_age_hours=24)

        assert removed == 1
        assert service.get_session(old_session.session_id) is None
        assert service.get_session(new_session.session_id) is not None
        # Verify old session's keys were cleared
        assert old_session.api_keys == {}

    def test_api_keys_not_persisted(self):
        """Test that API keys are truly not persisted."""
        service1 = SessionService()
        session = service1.create_session()
        session.set_api_key("openai", "sk-secret-key-12345")
        session_id = session.session_id

        # Key exists in memory
        assert session.get_api_key("openai") == "sk-secret-key-12345"

        # New service instance has no knowledge of the session
        service2 = SessionService()
        assert service2.get_session(session_id) is None


# =============================================================================
# ConfigService Tests
# =============================================================================


class TestConfigService:
    """Tests for the ConfigService."""

    @pytest.fixture
    def config_service(self) -> ConfigService:
        """Create a ConfigService pointing to the real configs directory."""
        return ConfigService(configs_dir=Path("configs"))

    def test_list_profiles(self, config_service: ConfigService):
        """Test listing all available profiles."""
        profiles = config_service.list_profiles()

        assert len(profiles) > 0
        names = [p.name for p in profiles]
        assert "cost-effective" in names
        assert "high-quality" in names

    def test_profile_summary_structure(self, config_service: ConfigService):
        """Test that profile summaries have correct structure."""
        profiles = config_service.list_profiles()

        for profile in profiles:
            assert isinstance(profile, ProfileSummary)
            assert profile.name != ""
            assert profile.root_model != ""
            assert profile.root_provider != ""
            assert profile.max_budget > 0

    def test_get_profile_names(self, config_service: ConfigService):
        """Test getting just profile names."""
        names = config_service.get_profile_names()

        assert isinstance(names, list)
        assert len(names) > 0
        assert all(isinstance(n, str) for n in names)
        assert "cost-effective" in names

    def test_load_profile(self, config_service: ConfigService):
        """Test loading a full profile."""
        config = config_service.load_profile("cost-effective")

        assert config.profile_name != ""
        assert config.root.provider in ["gemini", "openai", "ollama"]
        assert config.budget.max_usd > 0

    def test_load_profile_with_extension(self, config_service: ConfigService):
        """Test loading profile with .yaml extension."""
        config = config_service.load_profile("cost-effective.yaml")

        assert config.profile_name != ""

    def test_load_nonexistent_profile(self, config_service: ConfigService):
        """Test that loading a nonexistent profile raises error."""
        with pytest.raises(FileNotFoundError):
            config_service.load_profile("nonexistent-profile-12345")

    def test_load_with_keys(self, config_service: ConfigService):
        """Test loading profile with API keys attached."""
        api_keys = {"gemini": "test-key", "openai": "another-key"}

        config = config_service.load_with_keys("cost-effective", api_keys)

        assert hasattr(config, "api_keys")
        assert config.api_keys == api_keys  # type: ignore

    def test_validate_profile_valid(self, config_service: ConfigService):
        """Test validating a valid profile."""
        result = config_service.validate_profile("cost-effective")

        assert isinstance(result, ValidationResult)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_profile_nonexistent(self, config_service: ConfigService):
        """Test validating a nonexistent profile."""
        result = config_service.validate_profile("nonexistent")

        assert result.is_valid is False
        assert any("not found" in e.lower() for e in result.errors)

    def test_get_required_providers(self, config_service: ConfigService):
        """Test getting required providers for a profile."""
        providers = config_service.get_required_providers("cost-effective")

        assert isinstance(providers, list)
        # Gemini or OpenAI should be required (not ollama)
        assert "ollama" not in providers

    def test_profile_exists(self, config_service: ConfigService):
        """Test checking if profile exists."""
        assert config_service.profile_exists("cost-effective") is True
        assert config_service.profile_exists("cost-effective.yaml") is True
        assert config_service.profile_exists("nonexistent") is False

    def test_profile_summary_requires_methods(self, config_service: ConfigService):
        """Test ProfileSummary helper methods."""
        summary = config_service.get_profile_summary("cost-effective")

        assert summary is not None

        # Test requires_* properties work
        assert isinstance(summary.requires_gemini, bool)
        assert isinstance(summary.requires_openai, bool)
        assert isinstance(summary.requires_ollama, bool)

    def test_empty_configs_dir(self):
        """Test behavior with empty configs directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            service = ConfigService(configs_dir=Path(tmpdir))

            profiles = service.list_profiles()
            assert profiles == []

            names = service.get_profile_names()
            assert names == []


# =============================================================================
# Integration Tests (require real configs)
# =============================================================================


class TestConfigServiceIntegration:
    """Integration tests for ConfigService with real config files."""

    def test_all_profiles_valid(self):
        """Test that all shipped profiles are valid."""
        service = ConfigService()

        for name in service.get_profile_names():
            result = service.validate_profile(name)
            assert result.is_valid, f"Profile {name} is invalid: {result.errors}"

    def test_all_profiles_loadable(self):
        """Test that all shipped profiles can be loaded."""
        service = ConfigService()

        for name in service.get_profile_names():
            config = service.load_profile(name)
            assert config is not None
            assert config.root.provider in ["gemini", "openai", "ollama", "anthropic"]


# =============================================================================
# TaskService Tests (using mocks)
# =============================================================================


class TestTaskServiceMocked:
    """Tests for TaskService using mocked dependencies."""

    def test_get_api_keys_from_session(self):
        """Test that API keys are retrieved from session."""
        from src.rlm.services.task_service import TaskService

        config_service = ConfigService()
        session = Session()
        session.set_api_key("gemini", "session-key")

        task_service = TaskService(config_service, session)

        keys = task_service._get_api_keys()

        assert keys.get("gemini") == "session-key"

    def test_get_api_keys_from_env_fallback(self):
        """Test that API keys fall back to environment."""
        from src.rlm.services.task_service import TaskService

        config_service = ConfigService()
        session = Session()  # Empty session

        task_service = TaskService(config_service, session)

        # Set env var temporarily
        original = os.environ.get("GEMINI_API_KEY")
        os.environ["GEMINI_API_KEY"] = "env-key"

        try:
            keys = task_service._get_api_keys()
            assert keys.get("gemini") == "env-key"
        finally:
            if original:
                os.environ["GEMINI_API_KEY"] = original
            else:
                os.environ.pop("GEMINI_API_KEY", None)

    def test_validate_api_keys_missing(self):
        """Test that missing API keys raise ValueError."""
        from src.rlm.services.task_service import TaskService

        config_service = ConfigService()
        task_service = TaskService(config_service)

        config = config_service.load_profile("cost-effective")

        # Should raise if gemini key is missing for gemini profile
        if config.root.provider.lower() == "gemini":
            with pytest.raises(ValueError) as exc_info:
                task_service._validate_api_keys(config, {})
            assert "gemini" in str(exc_info.value).lower()

    def test_estimate_cost(self):
        """Test cost estimation."""
        from src.rlm.services.task_service import TaskService

        config_service = ConfigService()
        task_service = TaskService(config_service)

        estimate = task_service.estimate_cost(
            "cost-effective",
            estimated_input_tokens=10000,
            estimated_output_tokens=2000,
            estimated_steps=5,
        )

        assert "estimated_cost" in estimate
        assert "max_budget" in estimate
        assert estimate["estimated_cost"] >= 0
        assert estimate["max_budget"] > 0


class TestREPLPersistence:
    """Tests for REPL state persistence in TaskService."""

    def test_repl_storage_and_retrieval(self):
        """Test that REPL state is stored and can be retrieved."""
        from src.rlm.services.task_service import TaskService
        from src.core.repl import PythonREPL

        config_service = ConfigService()
        task_service = TaskService(config_service)

        # Clear any existing state
        task_service._repl_storage.clear()

        # Create a REPL with some state
        repl = PythonREPL()
        repl.execute("x = 42")
        repl.execute("y = 'hello'")

        # Manually store it
        task_id = "test-task-123"
        task_service._repl_storage[task_id] = repl

        # Check has_repl_state
        assert task_service.has_repl_state(task_id)
        assert not task_service.has_repl_state("nonexistent-task")

        # Retrieve and verify
        with task_service._storage_lock:
            retrieved_repl = task_service._repl_storage[task_id]

        # Variables are stored in locals dict
        assert retrieved_repl.locals.get("x") == 42
        assert retrieved_repl.locals.get("y") == "hello"

    def test_clear_repl_state(self):
        """Test that REPL state can be cleared."""
        from src.rlm.services.task_service import TaskService
        from src.core.repl import PythonREPL

        config_service = ConfigService()
        task_service = TaskService(config_service)

        # Store a REPL
        task_id = "test-task-456"
        repl = PythonREPL()
        repl.execute("z = 100")
        task_service._repl_storage[task_id] = repl

        # Verify it exists
        assert task_service.has_repl_state(task_id)

        # Clear it
        task_service.clear_repl_state(task_id)

        # Verify it's gone
        assert not task_service.has_repl_state(task_id)

        # Clearing nonexistent state should not raise
        task_service.clear_repl_state("nonexistent")

    def test_followup_without_repl_raises_error(self):
        """Test that run_followup raises ValueError if no REPL state exists."""
        from src.rlm.services.task_service import TaskService

        config_service = ConfigService()
        task_service = TaskService(config_service)

        # Clear any state
        task_service._repl_storage.clear()

        with pytest.raises(ValueError) as exc_info:
            task_service.run_followup(
                task_id="nonexistent-task",
                query="What is x?",
                config_name="cost-effective",
            )

        assert "No REPL state found" in str(exc_info.value)

