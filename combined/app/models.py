from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl


class CreateShortUrlRequest(BaseModel):
    url: HttpUrl
    custom_slug: str | None = Field(default=None, min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")


class ShortUrlResponse(BaseModel):
    slug: str
    short_url: str
    target_url: str
    created_at: datetime


class UrlStatsResponse(BaseModel):
    slug: str
    target_url: str
    created_at: datetime
    clicks: int
    last_accessed_at: datetime | None


class HealthResponse(BaseModel):
    status: str
    database: str


class ScenarioName(str, Enum):
    greenfield = "greenfield"
    brownfield = "brownfield"
    ambiguous = "ambiguous"


class RunWorkflowRequest(BaseModel):
    auto_approve: bool = False
    change_request: str | None = None


class ExecuteChangeRequest(BaseModel):
    requirement: str = Field(min_length=10, max_length=1000)
    auto_approve: bool = False


class ApprovalRequest(BaseModel):
    approved: bool
    approver: str = "human-reviewer"
    comment: str | None = None


