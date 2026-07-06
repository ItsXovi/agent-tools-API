from pydantic import BaseModel, Field
from typing import Optional


class CreateKeyRequest(BaseModel):
    label: Optional[str] = Field(default=None, description="Optional name for the key")
    tier: str = Field(default="free", description="free | indie | team")


class CreateKeyResponse(BaseModel):
    api_key: str
    key_id: str
    label: Optional[str] = None
    tier: str
    limit: int


class UsageResponse(BaseModel):
    conversions_used: int
    limit: int
    reset_at: str
    tier: str
    label: Optional[str] = None
