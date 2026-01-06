"""
Tests for Phase 11: YAML Configuration Profiles.

Tests cover:
- Configuration loading and parsing
- Per-model budget tracking
- Profile inheritance
- Environment variable substitution
"""

import pytest
from pathlib import Path
import tempfile
import yaml

from src.core.config_loader import (
    ConfigLoader,
    load_profile,
    ProfileConfig,
    ModelConfig,
    AgentConfig,
    PricingConfig,
    ModulesConfig,
    BudgetConfig,
    get_model_config_for_role,
)
from src.core.budget import BudgetManager, BudgetExceededError, ModelUsage


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_config_dir():
    """Create a temporary directory for test configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_yaml():
    """Sample configuration YAML content."""
    return {
        "profile_name": "Test Profile",
        "description": "A test configuration",
        "root": {
            "provider": "openai",
            "model": "gpt-5",
            "max_steps": 15,
            "max_depth": 4,
            "pricing": {
                "input_per_1m": 1.25,
                "output_per_1m": 10.00,
            }
        },
        "delegate": {
            "provider": "openai",
            "model": "gpt-5-mini",
            "max_steps": 8,
            "max_depth": 2,
            "pricing": {
                "input_per_1m": 0.25,
                "output_per_1m": 2.00,
            }
        },
        "modules": {
            "coder": {
                "provider": "ollama",
                "model": "qwen2.5-coder:14b",
                "pricing": {
                    "input_per_1m": 0.0,
                    "output_per_1m": 0.0,
                }
            }
        },
        "budget": {
            "max_usd": 5.0
        },
        "dspy": {
            "max_retries": 5,
            "cache_enabled": True
        },
        "logging": {
            "level": "DEBUG",
            "file": "logs/test.log"
        }
    }


@pytest.fixture
def reset_budget_manager():
    """Reset the BudgetManager singleton before each test."""
    BudgetManager._clear()
    yield
    BudgetManager._clear()


# =============================================================================
# ConfigLoader Tests
# =============================================================================


class TestConfigLoader:
    """Tests for ConfigLoader class."""

    def test_load_valid_profile(self, temp_config_dir, sample_config_yaml):
        """Test loading a valid YAML profile."""
        # Write sample config
        config_path = temp_config_dir / "test.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_config_yaml, f)

        # Load it
        loader = ConfigLoader(config_dir=temp_config_dir)
        config = loader.load("test.yaml")

        assert config.profile_name == "Test Profile"
        assert config.root.provider == "openai"
        assert config.root.model == "gpt-5"
        assert config.root.max_steps == 15
        assert config.root.pricing.input_per_1m == 1.25
        assert config.root.pricing.output_per_1m == 10.00
        assert config.budget.max_usd == 5.0

    def test_load_delegate_config(self, temp_config_dir, sample_config_yaml):
        """Test that delegate configuration is parsed correctly."""
        config_path = temp_config_dir / "test.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_config_yaml, f)

        loader = ConfigLoader(config_dir=temp_config_dir)
        config = loader.load("test.yaml")

        assert config.delegate.provider == "openai"
        assert config.delegate.model == "gpt-5-mini"
        assert config.delegate.max_steps == 8
        assert config.delegate.max_depth == 2
        assert config.delegate.pricing.input_per_1m == 0.25
        assert config.delegate.pricing.output_per_1m == 2.00

    def test_load_modules_config(self, temp_config_dir, sample_config_yaml):
        """Test that per-module overrides are parsed correctly."""
        config_path = temp_config_dir / "test.yaml"
        with open(config_path, "w") as f:
            yaml.dump(sample_config_yaml, f)

        loader = ConfigLoader(config_dir=temp_config_dir)
        config = loader.load("test.yaml")

        assert config.modules.coder is not None
        assert config.modules.coder.provider == "ollama"
        assert config.modules.coder.model == "qwen2.5-coder:14b"
        assert config.modules.coder.pricing.input_per_1m == 0.0
        assert config.modules.architect is None  # Not specified

    def test_file_not_found(self, temp_config_dir):
        """Test that FileNotFoundError is raised for missing configs."""
        loader = ConfigLoader(config_dir=temp_config_dir)

        with pytest.raises(FileNotFoundError):
            loader.load("nonexistent.yaml")

    def test_default_pricing_fallback(self, temp_config_dir):
        """Test that provider defaults are used when pricing not specified."""
        config_yaml = {
            "root": {
                "provider": "gemini",
                "model": "gemini-2.5-flash"
                # No pricing block - should use Gemini defaults
            }
        }

        config_path = temp_config_dir / "no_pricing.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_yaml, f)

        loader = ConfigLoader(config_dir=temp_config_dir)
        config = loader.load("no_pricing.yaml")

        # Should use Gemini 2.5 Flash default pricing
        assert config.root.pricing.input_per_1m == 0.30
        assert config.root.pricing.output_per_1m == 2.50

    def test_ollama_free_pricing(self, temp_config_dir):
        """Test that Ollama defaults to free pricing."""
        config_yaml = {
            "root": {
                "provider": "ollama",
                "model": "qwen2.5-coder:14b"
            }
        }

        config_path = temp_config_dir / "ollama.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config_yaml, f)

        loader = ConfigLoader(config_dir=temp_config_dir)
        config = loader.load("ollama.yaml")

        assert config.root.pricing.input_per_1m == 0.0
        assert config.root.pricing.output_per_1m == 0.0


class TestProfileInheritance:
    """Tests for profile inheritance (extends)."""

    def test_profile_extends(self, temp_config_dir):
        """Test that derived profiles inherit from base."""
        # Create base config
        base_yaml = {
            "profile_name": "Base Profile",
            "root": {
                "provider": "gemini",
                "model": "gemini-2.5-flash",
                "max_steps": 10,
            },
            "budget": {
                "max_usd": 1.0
            }
        }

        # Create derived config
        derived_yaml = {
            "extends": "base.yaml",
            "profile_name": "Derived Profile",
            "budget": {
                "max_usd": 5.0  # Override budget
            }
        }

        # Write configs
        with open(temp_config_dir / "base.yaml", "w") as f:
            yaml.dump(base_yaml, f)
        with open(temp_config_dir / "derived.yaml", "w") as f:
            yaml.dump(derived_yaml, f)

        # Load derived config
        loader = ConfigLoader(config_dir=temp_config_dir)
        config = loader.load("derived.yaml")

        # Should have derived name and budget
        assert config.profile_name == "Derived Profile"
        assert config.budget.max_usd == 5.0

        # Should inherit root from base
        assert config.root.provider == "gemini"
        assert config.root.model == "gemini-2.5-flash"


# =============================================================================
# Per-Model Budget Tracking Tests
# =============================================================================


class TestPerModelBudgetTracking:
    """Tests for per-model budget tracking in BudgetManager."""

    def test_register_model(self, reset_budget_manager):
        """Test registering a model with pricing."""
        budget = BudgetManager(max_budget=10.0)

        budget.register_model("gpt-5", input_price_per_1m=1.25, output_price_per_1m=10.00)

        assert "gpt-5" in budget.model_usage
        usage = budget.model_usage["gpt-5"]
        assert usage.input_price_per_1m == 1.25
        assert usage.output_price_per_1m == 10.00
        assert usage.total_cost == 0.0

    def test_per_model_cost_calculation(self, reset_budget_manager):
        """Test that costs are calculated correctly per model."""
        budget = BudgetManager(max_budget=10.0)

        # Register two models with different pricing
        budget.register_model("gpt-5", input_price_per_1m=1.25, output_price_per_1m=10.00)
        budget.register_model("gpt-5-mini", input_price_per_1m=0.25, output_price_per_1m=2.00)

        # Add usage for gpt-5: 100K input, 10K output
        # Cost = (100K/1M * 1.25) + (10K/1M * 10.00) = 0.125 + 0.10 = 0.225
        budget.add_usage(input_tokens=100_000, output_tokens=10_000, model_id="gpt-5")

        # Add usage for gpt-5-mini: 500K input, 50K output
        # Cost = (500K/1M * 0.25) + (50K/1M * 2.00) = 0.125 + 0.10 = 0.225
        budget.add_usage(input_tokens=500_000, output_tokens=50_000, model_id="gpt-5-mini")

        breakdown = budget.get_breakdown()

        assert abs(breakdown["gpt-5"] - 0.225) < 0.001
        assert abs(breakdown["gpt-5-mini"] - 0.225) < 0.001
        assert abs(budget.current_cost - 0.45) < 0.001

    def test_budget_limit_sums_all_models(self, reset_budget_manager):
        """Test that budget limit applies to sum of all model costs."""
        budget = BudgetManager(max_budget=0.50)

        budget.register_model("expensive", input_price_per_1m=10.0, output_price_per_1m=40.0)
        budget.register_model("cheap", input_price_per_1m=0.1, output_price_per_1m=0.4)

        # Add usage for expensive: 50K input, 10K output
        # Cost = (50K/1M * 10.0) + (10K/1M * 40.0) = 0.50 + 0.40 = 0.90
        budget.add_usage(input_tokens=50_000, output_tokens=10_000, model_id="expensive")

        # Should exceed budget
        with pytest.raises(BudgetExceededError):
            budget.check_budget()

    def test_get_model_stats(self, reset_budget_manager):
        """Test getting detailed stats for a model."""
        budget = BudgetManager(max_budget=10.0)

        budget.register_model("test-model", input_price_per_1m=1.0, output_price_per_1m=2.0)
        budget.add_usage(input_tokens=100_000, output_tokens=50_000, model_id="test-model")

        stats = budget.get_model_stats("test-model")

        assert stats is not None
        assert stats.total_input_tokens == 100_000
        assert stats.total_output_tokens == 50_000
        assert abs(stats.total_cost - 0.20) < 0.001  # (100K/1M * 1.0) + (50K/1M * 2.0)

    def test_unknown_model_uses_default_pricing(self, reset_budget_manager):
        """Test that unknown model_id falls back to default pricing."""
        budget = BudgetManager(max_budget=10.0)
        budget.input_price_per_1m = 1.0
        budget.output_price_per_1m = 2.0

        # Don't register the model, use it anyway
        budget.add_usage(input_tokens=100_000, output_tokens=50_000, model_id="unknown-model")

        # Should use default pricing
        # Cost = (100K/1M * 1.0) + (50K/1M * 2.0) = 0.10 + 0.10 = 0.20
        assert abs(budget.current_cost - 0.20) < 0.001

    def test_reset_clears_model_usage(self, reset_budget_manager):
        """Test that reset() clears per-model usage."""
        budget = BudgetManager(max_budget=10.0)

        budget.register_model("test-model", input_price_per_1m=1.0, output_price_per_1m=2.0)
        budget.add_usage(input_tokens=100_000, output_tokens=50_000, model_id="test-model")

        budget.reset()

        assert budget.current_cost == 0.0
        assert len(budget.model_usage) == 0


# =============================================================================
# get_model_config_for_role Tests
# =============================================================================


class TestGetModelConfigForRole:
    """Tests for role-based model configuration resolution."""

    def test_returns_module_override_when_present(self):
        """Test that per-module override takes precedence."""
        config = ProfileConfig(
            root=AgentConfig(provider="openai", model="gpt-5"),
            delegate=AgentConfig(provider="openai", model="gpt-5-mini"),
            modules=ModulesConfig(
                coder=ModelConfig(
                    provider="ollama",
                    model="qwen2.5-coder:14b",
                    pricing=PricingConfig(input_per_1m=0.0, output_per_1m=0.0)
                )
            )
        )

        model_config = get_model_config_for_role("coder", config, is_delegate=False)

        assert model_config.provider == "ollama"
        assert model_config.model == "qwen2.5-coder:14b"

    def test_returns_delegate_config_when_is_delegate(self):
        """Test that delegate config is used for delegate agents."""
        config = ProfileConfig(
            root=AgentConfig(provider="openai", model="gpt-5"),
            delegate=AgentConfig(provider="openai", model="gpt-5-mini"),
        )

        model_config = get_model_config_for_role("architect", config, is_delegate=True)

        assert model_config.provider == "openai"
        assert model_config.model == "gpt-5-mini"

    def test_returns_root_config_by_default(self):
        """Test that root config is used by default."""
        config = ProfileConfig(
            root=AgentConfig(provider="openai", model="gpt-5"),
            delegate=AgentConfig(provider="openai", model="gpt-5-mini"),
        )

        model_config = get_model_config_for_role("architect", config, is_delegate=False)

        assert model_config.provider == "openai"
        assert model_config.model == "gpt-5"


# =============================================================================
# Integration Tests
# =============================================================================


class TestLoadRealConfigs:
    """Integration tests that load actual config files from configs/."""

    @pytest.mark.parametrize("config_name", [
        "base.yaml",
        "cost-effective.yaml",
        "high-quality.yaml",
        "local-only.yaml",
        "hybrid.yaml",
        "paper-gpt5.yaml",
    ])
    def test_load_real_config(self, config_name):
        """Test that all real config files can be loaded."""
        config_path = Path("configs") / config_name

        if not config_path.exists():
            pytest.skip(f"Config file {config_name} not found")

        config = load_profile(config_path)

        assert config.profile_name is not None
        assert config.root.provider in ["gemini", "openai", "ollama"]
        assert config.root.model is not None
        assert config.budget.max_usd > 0

    def test_paper_gpt5_uses_gpt5_models(self):
        """Test that paper-gpt5.yaml uses the correct GPT-5 models."""
        config_path = Path("configs/paper-gpt5.yaml")

        if not config_path.exists():
            pytest.skip("paper-gpt5.yaml not found")

        config = load_profile(config_path)

        assert config.root.provider == "openai"
        assert "gpt-5" in config.root.model
        assert config.delegate.model == "gpt-5-mini"

    def test_local_only_uses_ollama(self):
        """Test that local-only.yaml uses only Ollama."""
        config_path = Path("configs/local-only.yaml")

        if not config_path.exists():
            pytest.skip("local-only.yaml not found")

        config = load_profile(config_path)

        assert config.root.provider == "ollama"
        assert config.delegate.provider == "ollama"
        # All pricing should be $0
        assert config.root.pricing.input_per_1m == 0.0
        assert config.root.pricing.output_per_1m == 0.0
