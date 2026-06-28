from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ScenarioName(str, Enum):
    greenfield = "greenfield"
    brownfield = "brownfield"
    ambiguous = "ambiguous"


class CreateLinkRequest(BaseModel):
    target_url: HttpUrl
    custom_endpoint: str | None = Field(default=None, min_length=3, max_length=64)
    expires_at: datetime | None = None
    max_clicks: int | None = Field(default=None, ge=1, le=1_000_000)

    @field_validator("custom_endpoint")
    @classmethod
    def endpoint_is_safe(cls, value: str | None) -> str | None:
        if value is None:
            return value
        allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
        if any(character not in allowed for character in value):
            raise ValueError("custom endpoint may only contain letters, numbers, hyphen, and underscore")
        blocked = {"api", "docs", "health", "static", "engineering", "r"}
        if value.lower() in blocked:
            raise ValueError("custom endpoint is reserved")
        return value


class LinkResponse(BaseModel):
    code: str
    short_url: str
    target_url: str
    created_at: datetime
    expires_at: datetime | None
    max_clicks: int | None
    clicks: int
    disabled: bool


class LinkStatsResponse(LinkResponse):
    last_outcome: str | None = None
    last_accessed_at: datetime | None = None


class ExecuteRequirementRequest(BaseModel):
    scenario: ScenarioName
    requirement: str = Field(min_length=10, max_length=1200)
    engineer_notes: str | None = Field(default=None, max_length=1200)
    engineer_signoff: bool = False


class HealthResponse(BaseModel):
    status: str
    database: str


class ErrorResponse(BaseModel):
    detail: str
