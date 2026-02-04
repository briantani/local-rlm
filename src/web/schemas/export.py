"""
Export and sharing schemas.
"""

from pydantic import BaseModel


class ShareResponse(BaseModel):
    """Response for share operation."""
    share_url: str
    share_id: str
    expires_at: str | None = None
