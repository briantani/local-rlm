"""
Configuration Loader for YAML-based profiles.

Implements Phase 11: YAML Configuration Profiles for multi-model setups.
Allows different models for root vs. delegate agents, and per-module overrides.
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class PricingConfig:
    """Pricing information for a model."""
    input_per_1m: float = 0.30   # Default: Gemini 2.5 Flash
    output_per_1m: float = 2.50


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: str
    model: str
    pricing: PricingConfig = field(default_factory=PricingConfig)

    @property
    def model_id(self) -> str:
        """Generate a unique model identifier."""
        return f"{self.provider}/{self.model}"


@dataclass
class AgentConfig:
    """Configuration for an agent (root or delegate)."""
    provider: str
    model: str
    max_steps: int = 10
    max_depth: int = 3
    pricing: PricingConfig = field(default_factory=PricingConfig)

    @property
    def model_id(self) -> str:
        """Generate a unique model identifier."""
        return f"{self.provider}/{self.model}"

    def to_model_config(self) -> ModelConfig:
        """Convert to ModelConfig."""
        return ModelConfig(
            provider=self.provider,
            model=self.model,
            pricing=self.pricing
        )


@dataclass
class ModulesConfig:
    """Per-module model overrides."""
    architect: ModelConfig | None = None
    coder: ModelConfig | None = None
    responder: ModelConfig | None = None
    delegator: ModelConfig | None = None


@dataclass
class BudgetConfig:
    """Budget configuration."""
    max_usd: float = 1.0


@dataclass
class DSPyConfig:
    """DSPy framework configuration."""
    max_retries: int = 3
    cache_enabled: bool = True


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    file: str | None = None


@dataclass
class ProfileConfig:
    """Complete configuration profile."""
    profile_name: str = "Default Profile"
    description: str = ""
    root: AgentConfig = field(default_factory=lambda: AgentConfig(
        provider="gemini", model="gemini-2.5-flash"
    ))
    delegate: AgentConfig = field(default_factory=lambda: AgentConfig(
        provider="gemini", model="gemini-2.5-flash-lite", max_steps=5, max_depth=1
    ))
    modules: ModulesConfig = field(default_factory=ModulesConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    dspy: DSPyConfig = field(default_factory=DSPyConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)


# =============================================================================
# Config Loader
# =============================================================================


class ConfigLoader:
    """Loads and validates YAML configuration profiles."""

    # Default pricing by provider (fallback if not specified in config)
    DEFAULT_PRICING: dict[str, PricingConfig] = {
        "gemini": PricingConfig(input_per_1m=0.30, output_per_1m=2.50),  # Gemini 2.5 Flash
        "openai": PricingConfig(input_per_1m=0.25, output_per_1m=2.00),  # GPT-5-mini
        "ollama": PricingConfig(input_per_1m=0.0, output_per_1m=0.0),    # Local = free
    }

    def __init__(self, config_dir: Path | None = None):
        """
        Initialize the config loader.

        Args:
            config_dir: Directory containing config files. Defaults to configs/
        """
        self.config_dir = config_dir or Path("configs")

    def load(self, path: str | Path) -> ProfileConfig:
        """
        Load a configuration profile from a YAML file.

        Args:
            path: Path to the YAML file (absolute or relative to CWD)

        Returns:
            Parsed ProfileConfig

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config is invalid
        """
        config_path = Path(path)

        # If not absolute and doesn't exist, try relative to config_dir
        if not config_path.is_absolute() and not config_path.exists():
            potential_path = self.config_dir / config_path
            if potential_path.exists():
                config_path = potential_path

        if not config_path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(config_path, "r") as f:
            raw_config = yaml.safe_load(f)

        # Handle inheritance (extends)
        if "extends" in raw_config:
            base_path = raw_config.pop("extends")
            base_config = self.load(base_path)
            raw_config = self._merge_configs(
                self._profile_to_dict(base_config),
                raw_config
            )

        # Substitute environment variables
        raw_config = self._substitute_env_vars(raw_config)

        # Parse into dataclasses
        return self._parse_config(raw_config)

    def _parse_config(self, raw: dict[str, Any]) -> ProfileConfig:
        """Parse raw YAML dict into ProfileConfig dataclass."""

        # Parse root agent config
        root_raw = raw.get("root", {})
        root = self._parse_agent_config(root_raw, is_delegate=False)

        # Parse delegate agent config
        delegate_raw = raw.get("delegate", {})
        delegate = self._parse_agent_config(delegate_raw, is_delegate=True)

        # Parse modules config
        modules = self._parse_modules_config(raw.get("modules", {}))

        # Parse budget config
        budget_raw = raw.get("budget", {})
        budget = BudgetConfig(
            max_usd=budget_raw.get("max_usd", 1.0)
        )

        # Parse DSPy config
        dspy_raw = raw.get("dspy", {})
        dspy_config = DSPyConfig(
            max_retries=dspy_raw.get("max_retries", 3),
            cache_enabled=dspy_raw.get("cache_enabled", True)
        )

        # Parse logging config
        logging_raw = raw.get("logging", {})
        logging_config = LoggingConfig(
            level=logging_raw.get("level", "INFO"),
            file=logging_raw.get("file")
        )

        return ProfileConfig(
            profile_name=raw.get("profile_name", "Default Profile"),
            description=raw.get("description", ""),
            root=root,
            delegate=delegate,
            modules=modules,
            budget=budget,
            dspy=dspy_config,
            logging=logging_config
        )

    def _parse_agent_config(
        self,
        raw: dict[str, Any],
        is_delegate: bool = False
    ) -> AgentConfig:
        """Parse agent configuration from raw dict."""
        provider = raw.get("provider", "gemini")
        model = raw.get("model", "gemini-2.5-flash-lite" if is_delegate else "gemini-2.5-flash")

        # Parse pricing (with provider defaults as fallback)
        pricing = self._parse_pricing(raw.get("pricing"), provider)

        return AgentConfig(
            provider=provider,
            model=model,
            max_steps=raw.get("max_steps", 5 if is_delegate else 10),
            max_depth=raw.get("max_depth", 1 if is_delegate else 3),
            pricing=pricing
        )

    def _parse_model_config(
        self,
        raw: dict[str, Any]
    ) -> ModelConfig:
        """Parse model configuration from raw dict."""
        provider = raw.get("provider", "gemini")
        model = raw.get("model", "gemini-2.5-flash")

        pricing = self._parse_pricing(raw.get("pricing"), provider)

        return ModelConfig(
            provider=provider,
            model=model,
            pricing=pricing
        )

    def _parse_modules_config(self, raw: dict[str, Any]) -> ModulesConfig:
        """Parse per-module configuration."""
        modules = ModulesConfig()

        for role in ["architect", "coder", "responder", "delegator"]:
            if role in raw:
                model_config = self._parse_model_config(raw[role])
                setattr(modules, role, model_config)

        return modules

    def _parse_pricing(
        self,
        raw: dict[str, Any] | None,
        provider: str
    ) -> PricingConfig:
        """Parse pricing config with provider defaults as fallback."""
        if raw:
            return PricingConfig(
                input_per_1m=raw.get("input_per_1m", 0.0),
                output_per_1m=raw.get("output_per_1m", 0.0)
            )

        # Use provider defaults
        default = self.DEFAULT_PRICING.get(provider.lower())
        if default:
            return PricingConfig(
                input_per_1m=default.input_per_1m,
                output_per_1m=default.output_per_1m
            )

        # Unknown provider, log warning
        logger.warning(f"Unknown provider '{provider}', using zero pricing")
        return PricingConfig(input_per_1m=0.0, output_per_1m=0.0)

    def _substitute_env_vars(self, config: Any) -> Any:
        """Recursively substitute ${VAR} patterns with environment variables."""
        if isinstance(config, str):
            # Match ${VAR_NAME} pattern
            if config.startswith("${") and config.endswith("}"):
                var_name = config[2:-1]
                value = os.getenv(var_name)
                if value is None:
                    logger.warning(f"Environment variable {var_name} not found")
                    return config
                return value
            return config
        elif isinstance(config, dict):
            return {k: self._substitute_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_env_vars(item) for item in config]
        return config

    def _merge_configs(
        self,
        base: dict[str, Any],
        override: dict[str, Any]
    ) -> dict[str, Any]:
        """Deep merge override config into base config."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _profile_to_dict(self, profile: ProfileConfig) -> dict[str, Any]:
        """Convert ProfileConfig back to dict for merging."""
        # Simple conversion - could use dataclasses.asdict but need custom handling
        return {
            "profile_name": profile.profile_name,
            "description": profile.description,
            "root": {
                "provider": profile.root.provider,
                "model": profile.root.model,
                "max_steps": profile.root.max_steps,
                "max_depth": profile.root.max_depth,
                "pricing": {
                    "input_per_1m": profile.root.pricing.input_per_1m,
                    "output_per_1m": profile.root.pricing.output_per_1m,
                }
            },
            "delegate": {
                "provider": profile.delegate.provider,
                "model": profile.delegate.model,
                "max_steps": profile.delegate.max_steps,
                "max_depth": profile.delegate.max_depth,
                "pricing": {
                    "input_per_1m": profile.delegate.pricing.input_per_1m,
                    "output_per_1m": profile.delegate.pricing.output_per_1m,
                }
            },
            "budget": {
                "max_usd": profile.budget.max_usd,
            },
            "dspy": {
                "max_retries": profile.dspy.max_retries,
                "cache_enabled": profile.dspy.cache_enabled,
            },
            "logging": {
                "level": profile.logging.level,
                "file": profile.logging.file,
            }
        }


# =============================================================================
# Helper Functions
# =============================================================================


def load_profile(path: str | Path) -> ProfileConfig:
    """
    Convenience function to load a configuration profile.

    Args:
        path: Path to the YAML configuration file

    Returns:
        Parsed ProfileConfig
    """
    loader = ConfigLoader()
    return loader.load(path)


def get_model_config_for_role(
    role: str,
    config: ProfileConfig,
    is_delegate: bool = False
) -> ModelConfig:
    """
    Get the ModelConfig for a specific role.

    Resolution order:
    1. Per-module override (config.modules.{role})
    2. Delegate config (if is_delegate=True)
    3. Root config (default)

    Args:
        role: The role name ("architect", "coder", "responder", "delegator")
        config: The ProfileConfig
        is_delegate: Whether this is for a delegate agent

    Returns:
        ModelConfig for the role
    """
    # Check for per-module override
    module_config = getattr(config.modules, role, None)
    if module_config is not None:
        return module_config

    # Use delegate or root config
    agent_config = config.delegate if is_delegate else config.root
    return agent_config.to_model_config()
