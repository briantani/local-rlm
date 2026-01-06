"""
Configuration Routes.

Handles listing and viewing configuration profiles.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from src.rlm.services import ConfigService
from src.rlm.services.config_service import ProfileSummary
from src.web.dependencies import get_config_service

router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================


class ProfileSummaryResponse(BaseModel):
    """Summary of a configuration profile."""
    name: str
    description: str
    root_model: str
    root_provider: str
    delegate_model: str
    delegate_provider: str
    max_budget: float
    max_steps: int
    max_depth: int
    requires_gemini: bool
    requires_openai: bool
    requires_ollama: bool
    required_providers: list[str]

    @classmethod
    def from_summary(cls, summary: ProfileSummary) -> "ProfileSummaryResponse":
        """Create from a ProfileSummary."""
        return cls(
            name=summary.name,
            description=summary.description,
            root_model=summary.root_model,
            root_provider=summary.root_provider,
            delegate_model=summary.delegate_model,
            delegate_provider=summary.delegate_provider,
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


class ProfileListResponse(BaseModel):
    """Response for listing profiles."""
    profiles: list[ProfileSummaryResponse]
    count: int


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=ProfileListResponse)
async def list_profiles(
    config_service: ConfigService = Depends(get_config_service),
) -> ProfileListResponse:
    """
    List all available configuration profiles.

    Returns summary information about each profile including
    required API keys and budget limits.
    """
    summaries = config_service.list_profiles()
    profiles = [ProfileSummaryResponse.from_summary(s) for s in summaries]

    return ProfileListResponse(
        profiles=profiles,
        count=len(profiles),
    )


@router.get("/{name}", response_model=ProfileDetailResponse)
async def get_profile(
    name: str,
    config_service: ConfigService = Depends(get_config_service),
) -> ProfileDetailResponse:
    """
    Get detailed information about a specific profile.

    Includes validation status and any errors or warnings.
    """
    summary = config_service.get_profile_summary(name)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found: {name}. Use GET /api/configs to list available profiles.",
        )

    validation = config_service.validate_profile(name)

    return ProfileDetailResponse(
        name=summary.name,
        description=summary.description,
        root_model=summary.root_model,
        root_provider=summary.root_provider,
        delegate_model=summary.delegate_model,
        delegate_provider=summary.delegate_provider,
        max_budget=summary.max_budget,
        max_steps=summary.max_steps,
        max_depth=summary.max_depth,
        requires_gemini=summary.requires_gemini,
        requires_openai=summary.requires_openai,
        requires_ollama=summary.requires_ollama,
        required_providers=summary.get_required_providers(),
        is_valid=validation.is_valid,
        validation_errors=validation.errors,
        validation_warnings=validation.warnings,
    )


@router.get("/{name}/estimate")
async def estimate_cost(
    name: str,
    input_tokens: int = 10000,
    output_tokens: int = 2000,
    steps: int = 5,
    config_service: ConfigService = Depends(get_config_service),
):
    """
    Estimate the cost for running a task with this profile.

    Args:
        name: Profile name
        input_tokens: Estimated input tokens per step
        output_tokens: Estimated output tokens per step
        steps: Estimated number of steps
    """
    if not config_service.profile_exists(name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Profile not found: {name}",
        )

    # Create a temporary TaskService to use its estimate method
    from src.rlm.services import TaskService
    task_service = TaskService(config_service)

    estimate = task_service.estimate_cost(
        config_name=name,
        estimated_input_tokens=input_tokens,
        estimated_output_tokens=output_tokens,
        estimated_steps=steps,
    )

    return estimate
