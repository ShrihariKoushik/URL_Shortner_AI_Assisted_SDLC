from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse

from app.audit import AuditLogger
from app.config import Settings, get_settings
from app.database import Database
from app.llm import LlmClient
from app.models import (
    ApprovalRequest,
    CreateShortUrlRequest,
    HealthResponse,
    RunWorkflowRequest,
    ScenarioName,
    ShortUrlResponse,
    UrlStatsResponse,
)
from app.orchestrator import SdlcOrchestrator
from app.url_service import SlugAlreadyExistsError, UrlNotFoundError, UrlService

app = FastAPI(
    title="Agentic URL Shortener",
    version="0.1.0",
    description="URL shortener with DAG-based agentic SDLC orchestration.",
)


@lru_cache
def get_database() -> Database:
    return Database(get_settings().database_url)


def get_url_service(settings: Settings = Depends(get_settings)) -> UrlService:
    return UrlService(get_database(), settings.base_url, settings.slug_length)


@lru_cache
def get_orchestrator() -> SdlcOrchestrator:
    settings = get_settings()
    return SdlcOrchestrator(
        audit=AuditLogger(settings.audit_log_path),
        llm=LlmClient(settings.openai_api_key, settings.openai_model),
        require_human_approval=settings.require_human_approval,
    )


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        with get_database().connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return HealthResponse(status="ok", database="ok")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc


@app.post("/shorten", response_model=ShortUrlResponse, status_code=status.HTTP_201_CREATED)
def shorten(request: CreateShortUrlRequest, service: UrlService = Depends(get_url_service)):
    try:
        return service.create(str(request.url), request.custom_slug)
    except SlugAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail="slug already exists") from exc


@app.get("/stats/{slug}", response_model=UrlStatsResponse)
def stats(slug: str, service: UrlService = Depends(get_url_service)):
    try:
        return service.get(slug)
    except UrlNotFoundError as exc:
        raise HTTPException(status_code=404, detail="slug not found") from exc


@app.get("/{slug}", include_in_schema=False)
def redirect(slug: str, service: UrlService = Depends(get_url_service)):
    try:
        return RedirectResponse(service.resolve(slug), status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except UrlNotFoundError as exc:
        raise HTTPException(status_code=404, detail="slug not found") from exc


@app.post("/agent/scenarios/{scenario}/run")
def run_scenario(scenario: ScenarioName, request: RunWorkflowRequest):
    return get_orchestrator().start(scenario.value, request.change_request, request.auto_approve)


@app.get("/agent/runs/{run_id}")
def get_run(run_id: str):
    try:
        return get_orchestrator().get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="workflow run not found") from exc


@app.post("/agent/runs/{run_id}/approve/{node_id}")
def approve_run(run_id: str, node_id: str, request: ApprovalRequest):
    try:
        return get_orchestrator().approve(run_id, node_id, request.approved, request.approver, request.comment)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="workflow run not found") from exc

