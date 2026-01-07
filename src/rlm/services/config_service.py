"""
Configuration Service for RLM.

Manages loading, listing, and validating configuration profiles.
Wraps the config_loader functionality with a service interface.

Phase 12: Core Library Refactoring
"""

import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from src.core.config_loader import (
    ConfigLoader,
    ProfileConfig,
)


logger = logging.getLogger(__name__)


@dataclass
class ProfileSummary:
    """
    Summary information about a configuration profile.

    Used for listing profiles without loading full configuration.
    """
    name: str
    description: str
    root_model: str
    root_provider: str
    delegate_model: str
    delegate_provider: str
    coder_model: str
    coder_provider: str
    max_budget: float
    max_steps: int
    max_depth: int

    @property
    def requires_gemini(self) -> bool:
        """Check if profile requires Gemini API key."""
        providers = [self.root_provider.lower(), self.delegate_provider.lower(), self.coder_provider.lower()]
        return any("gemini" in p for p in providers)

    @property
    def requires_openai(self) -> bool:
        """Check if profile requires OpenAI API key."""
        providers = [self.root_provider.lower(), self.delegate_provider.lower(), self.coder_provider.lower()]
        return any("openai" in p for p in providers)

    @property
    def requires_ollama(self) -> bool:
        """Check if profile requires Ollama (local, no key needed)."""
        providers = [self.root_provider.lower(), self.delegate_provider.lower(), self.coder_provider.lower()]
        return any("ollama" in p for p in providers)

    def get_required_providers(self) -> list[str]:
        """
        Get list of providers that require API keys.

        Returns:
            List of provider names (excludes ollama which is local)
        """
        providers = set()
        for provider in [self.root_provider.lower(), self.delegate_provider.lower(), self.coder_provider.lower()]:
            if provider != "ollama" and provider != "unknown":
                providers.add(provider)
        return list(providers)


@dataclass
class ValidationResult:
    """Result of validating a configuration profile."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class ConfigService:
    """
    Service for managing configuration profiles.

    Provides a clean interface for:
    - Listing available profiles
    - Loading profiles with or without API keys
    - Validating profiles
    - Getting profile summaries
    """

    # Known provider names for validation
    KNOWN_PROVIDERS = {"gemini", "openai", "ollama", "anthropic"}

    def __init__(self, configs_dir: Path | str = Path("configs")):
        """
        Initialize the config service.

        Args:
            configs_dir: Directory containing YAML configuration files
        """
        self.configs_dir = Path(configs_dir)
        self._loader = ConfigLoader(config_dir=self.configs_dir)

    def list_profiles(self) -> list[ProfileSummary]:
        """
        List all available configuration profiles with summary metadata.

        Returns:
            List of ProfileSummary objects for each YAML file in configs_dir
        """
        profiles = []

        if not self.configs_dir.exists():
            logger.warning(f"Configs directory does not exist: {self.configs_dir}")
            return profiles

        for yaml_file in sorted(self.configs_dir.glob("*.yaml")):
            try:
                summary = self._get_profile_summary(yaml_file)
                if summary:
                    profiles.append(summary)
            except Exception as e:
                logger.warning(f"Failed to parse {yaml_file.name}: {e}")
                continue

        return profiles

    def _get_profile_summary(self, yaml_path: Path) -> ProfileSummary | None:
        """
        Get summary information from a YAML config file.

        Args:
            yaml_path: Path to the YAML file

        Returns:
            ProfileSummary or None if parsing fails
        """
        try:
            with open(yaml_path, "r") as f:
                raw = yaml.safe_load(f)

            if not raw:
                return None

            root = raw.get("root", {})
            delegate = raw.get("delegate", {})
            budget = raw.get("budget", {})
            modules = raw.get("modules", {})
            coder = modules.get("coder", {})

            # If no coder module, use "(uses root model)" as display text
            coder_model = coder.get("model", "(uses root model)")
            coder_provider = coder.get("provider", root.get("provider", "unknown"))

            return ProfileSummary(
                name=yaml_path.stem,
                description=raw.get("description", ""),
                root_model=root.get("model", "unknown"),
                root_provider=root.get("provider", "unknown"),
                delegate_model=delegate.get("model", "unknown"),
                delegate_provider=delegate.get("provider", "unknown"),
                coder_model=coder_model,
                coder_provider=coder_provider,
                max_budget=budget.get("max_usd", 1.0),
                max_steps=root.get("max_steps", 10),
                max_depth=root.get("max_depth", 3),
            )
        except Exception as e:
            logger.error(f"Error parsing {yaml_path}: {e}")
            return None

    def get_profile_names(self) -> list[str]:
        """
        Get just the names of available profiles.

        Returns:
            List of profile names (without .yaml extension)
        """
        if not self.configs_dir.exists():
            return []
        return [f.stem for f in sorted(self.configs_dir.glob("*.yaml"))]

    def load_profile(self, name: str) -> ProfileConfig:
        """
        Load a profile by name.

        Args:
            name: Profile name (with or without .yaml extension)

        Returns:
            Fully parsed ProfileConfig

        Raises:
            FileNotFoundError: If profile doesn't exist
            ValueError: If profile is invalid
        """
        # Normalize name
        if name.endswith(".yaml"):
            name = name[:-5]

        config_path = self.configs_dir / f"{name}.yaml"
        return self._loader.load(config_path)

    def load_profile_from_path(self, path: Path | str) -> ProfileConfig:
        """
        Load a profile from a specific path.

        Args:
            path: Full path to the YAML file

        Returns:
            Fully parsed ProfileConfig
        """
        return self._loader.load(Path(path))

    def load_with_keys(
        self,
        name: str,
        api_keys: dict[str, str]
    ) -> ProfileConfig:
        """
        Load a profile and inject runtime API keys.

        The API keys are attached to the config object for use by
        get_lm_for_role() without being persisted.

        Args:
            name: Profile name
            api_keys: Dict mapping provider names to API keys

        Returns:
            ProfileConfig with api_keys attribute set
        """
        config = self.load_profile(name)
        # Attach API keys to config (not persisted, just for runtime use)
        # We use a dynamic attribute since ProfileConfig is a dataclass
        config.api_keys = api_keys  # type: ignore
        return config

    def get_profile_summary(self, name: str) -> ProfileSummary | None:
        """
        Get summary for a specific profile by name.

        Args:
            name: Profile name

        Returns:
            ProfileSummary or None if not found
        """
        if name.endswith(".yaml"):
            name = name[:-5]

        yaml_path = self.configs_dir / f"{name}.yaml"
        if yaml_path.exists():
            return self._get_profile_summary(yaml_path)
        return None

    def validate_profile(self, name: str) -> ValidationResult:
        """
        Validate a configuration profile.

        Args:
            name: Profile name

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        try:
            config = self.load_profile(name)
        except FileNotFoundError:
            return ValidationResult(
                is_valid=False,
                errors=[f"Profile not found: {name}"],
                warnings=[]
            )
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Failed to parse profile: {e}"],
                warnings=[]
            )

        # Check providers
        for role, provider in [("root", config.root.provider),
                               ("delegate", config.delegate.provider)]:
            if provider.lower() not in self.KNOWN_PROVIDERS:
                warnings.append(f"Unknown provider '{provider}' for {role}")

        # Check budget
        if config.budget.max_usd <= 0:
            errors.append("Budget max_usd must be positive")
        elif config.budget.max_usd > 100:
            warnings.append("Budget is very high (>$100)")

        # Check steps/depth
        if config.root.max_steps <= 0:
            errors.append("max_steps must be positive")
        if config.root.max_depth < 0:
            errors.append("max_depth cannot be negative")
        if config.root.max_depth > 5:
            warnings.append("max_depth > 5 may cause excessive recursion")

        # Check pricing
        if config.root.pricing.input_per_1m < 0:
            errors.append("Pricing cannot be negative")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def get_required_providers(self, name: str) -> list[str]:
        """
        Get list of providers that require API keys for a profile.

        Args:
            name: Profile name

        Returns:
            List of provider names (excludes ollama)
        """
        summary = self.get_profile_summary(name)
        if summary:
            return summary.get_required_providers()
        return []

    def profile_exists(self, name: str) -> bool:
        """
        Check if a profile exists.

        Args:
            name: Profile name

        Returns:
            True if profile exists
        """
        if name.endswith(".yaml"):
            name = name[:-5]
        return (self.configs_dir / f"{name}.yaml").exists()
