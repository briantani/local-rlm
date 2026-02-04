"""
API Key Manager.

Handles API key retrieval, validation, and environment configuration.
Extracted from TaskService for better separation of concerns.

Phase 6: Service Layer Refactoring
"""

import logging
import os

from src.core.config_loader import ProfileConfig
from src.rlm.services.session_service import Session


logger = logging.getLogger(__name__)


class ApiKeyManager:
    """
    Manages API keys for LLM providers.

    Handles:
    - Retrieving keys from session or environment
    - Validating required keys against config
    - Configuring environment variables for DSPy
    """

    # Environment variable mappings
    ENV_MAPPINGS = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
    }

    def __init__(self, session: Session | None = None):
        """
        Initialize the API key manager.

        Args:
            session: Optional session with API keys
        """
        self.session = session

    def get_api_keys(self) -> dict[str, str]:
        """
        Get API keys from session or environment variables.

        Priority:
        1. Session API keys (if session exists)
        2. Environment variables (fallback)

        Returns:
            Dict mapping provider names to API keys
        """
        api_keys: dict[str, str] = {}

        # Try session first
        if self.session:
            api_keys.update(self.session.api_keys)

        # Fill in missing keys from environment
        for provider, env_var in self.ENV_MAPPINGS.items():
            if provider not in api_keys:
                value = os.getenv(env_var)
                if value:
                    api_keys[provider] = value

        return api_keys

    def validate_api_keys(
        self,
        config: ProfileConfig,
        api_keys: dict[str, str]
    ) -> None:
        """
        Validate that required API keys are present.

        Args:
            config: The profile configuration
            api_keys: Available API keys

        Raises:
            ValueError: If required keys are missing
        """
        required_providers = self._get_required_providers(config)
        missing = [p for p in required_providers if p not in api_keys]

        if missing:
            raise ValueError(
                f"Missing API keys for providers: {', '.join(missing)}. "
                f"Set them in the session or environment variables."
            )

    def configure_environment(self, api_keys: dict[str, str]) -> None:
        """
        Configure environment variables for DSPy.

        DSPy reads API keys from environment, so we need to set them
        from our session/runtime keys.

        Args:
            api_keys: Dict of API keys
        """
        for provider, env_var in self.ENV_MAPPINGS.items():
            if provider in api_keys:
                os.environ[env_var] = api_keys[provider]
                logger.debug(f"Set {env_var} for provider {provider}")

    def _get_required_providers(self, config: ProfileConfig) -> set[str]:
        """
        Extract required providers from config.

        Args:
            config: The profile configuration

        Returns:
            Set of provider names (lowercase) that require API keys
        """
        required_providers = set()

        # Check root and delegate providers
        for provider in [config.root.provider, config.delegate.provider]:
            provider = provider.lower()
            if provider != "ollama":  # Ollama is local, no key needed
                required_providers.add(provider)

        # Check module overrides
        if config.modules:
            for module in [
                config.modules.architect,
                config.modules.coder,
                config.modules.responder,
                config.modules.delegator,
            ]:
                if module and module.provider.lower() != "ollama":
                    required_providers.add(module.provider.lower())

        return required_providers
