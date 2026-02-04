"""
Configuration profile schemas for the web API.
"""

from pydantic import BaseModel


class ProfileSummaryResponse(BaseModel):
    """Summary of a configuration profile."""
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
    requires_gemini: bool
    requires_openai: bool
    requires_ollama: bool
    required_providers: list[str]

    @classmethod
    def from_summary(cls, summary: any) -> "ProfileSummaryResponse":
        """Create from a ProfileSummary."""
        return cls(
            name=summary.name,
            description=summary.description,
            root_model=summary.root_model,
            root_provider=summary.root_provider,
            delegate_model=summary.delegate_model,
            delegate_provider=summary.delegate_provider,
            coder_model=summary.coder_model,
            coder_provider=summary.coder_provider,
            max_budget=summary.max_budget,
            max_steps=summary.max_steps,
            max_depth=summary.max_depth,
            requires_gemini=summary.requires_gemini,
            requires_openai=summary.requires_openai,
            requires_ollama=summary.requires_ollama,
            required_providers=summary.get_required_providers(),
        )


class ProfileDetailResponse(ProfileSummaryResponse):
    """Detailed profile information."""
    is_valid: bool
    validation_errors: list[str]
    validation_warnings: list[str]
