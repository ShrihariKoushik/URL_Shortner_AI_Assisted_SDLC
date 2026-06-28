from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.database import Database
from app.engineering import EngineeringEvidenceService
from app.implementation import SecureImplementationService
from app.schemas import CreateLinkRequest, ExecuteRequirementRequest, HealthResponse, ImplementRequirementRequest, LinkResponse, LinkStatsResponse
from app.url_service import (
    LinkAlreadyExistsError,
    LinkClickLimitExceededError,
    LinkDisabledError,
    LinkExpiredError,
    LinkNotFoundError,
    UrlService,
)

app = FastAPI(
    title="AI-Assisted URL Shortener",
    version="0.1.0",
    description="Engineer-led AI-assisted URL shortener with reviewable engineering evidence.",
)

STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@lru_cache
def get_database() -> Database:
    return Database(get_settings().database_file)


def get_url_service(settings: Settings = Depends(get_settings)) -> UrlService:
    return UrlService(get_database(), settings.public_base_url)


@lru_cache
def get_engineering_service() -> EngineeringEvidenceService:
    settings = get_settings()
    return EngineeringEvidenceService(
        get_database(),
        require_signoff=settings.require_engineer_signoff,
        settings=settings,
    )


@lru_cache
def get_implementation_service() -> SecureImplementationService:
    return SecureImplementationService(Path(__file__).resolve().parents[1], get_settings())


@app.get("/", include_in_schema=False)
def console() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        with get_database().connect() as connection:
            connection.execute("SELECT 1").fetchone()
        return HealthResponse(status="ok", database="ok")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"database unavailable: {exc}") from exc


@app.post("/api/links", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
def create_link(request: CreateLinkRequest, service: UrlService = Depends(get_url_service)) -> LinkResponse:
    try:
        return service.create(
            str(request.target_url),
            custom_endpoint=request.custom_endpoint,
            expires_at=request.expires_at,
            max_clicks=request.max_clicks,
        )
    except LinkAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail="custom endpoint already exists") from exc


@app.get("/api/links/{code}/stats", response_model=LinkStatsResponse)
def get_stats(code: str, service: UrlService = Depends(get_url_service)) -> LinkStatsResponse:
    try:
        return service.get(code)
    except LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="short link not found") from exc


@app.post("/api/links/{code}/disable", response_model=LinkStatsResponse)
def disable_link(code: str, service: UrlService = Depends(get_url_service)) -> LinkStatsResponse:
    try:
        return service.disable(code)
    except LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="short link not found") from exc


@app.get("/r/{code}", include_in_schema=False)
def redirect(
    code: str,
    request: Request,
    user_agent: str | None = Header(default=None),
    service: UrlService = Depends(get_url_service),
) -> RedirectResponse:
    try:
        target = service.resolve(code, user_agent=user_agent, referrer=request.headers.get("referer"))
        return RedirectResponse(target, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except LinkNotFoundError as exc:
        raise HTTPException(status_code=404, detail="short link not found") from exc
    except LinkExpiredError as exc:
        raise HTTPException(status_code=410, detail="short link expired") from exc
    except LinkClickLimitExceededError as exc:
        raise HTTPException(status_code=429, detail="short link click limit exceeded") from exc
    except LinkDisabledError as exc:
        raise HTTPException(status_code=410, detail="short link disabled") from exc


@app.post("/engineering/execute")
def execute_requirement(
    request: ExecuteRequirementRequest,
    service: EngineeringEvidenceService = Depends(get_engineering_service),
):
    return service.execute(
        request.scenario,
        request.requirement,
        request.engineer_notes,
        request.engineer_signoff,
        request.approval_role,
        request.engineer_actions,
    )


@app.get("/engineering/runs/{run_id}")
def get_engineering_run(run_id: str, service: EngineeringEvidenceService = Depends(get_engineering_service)):
    try:
        return service.get(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="engineering run not found") from exc


@app.get("/engineering/runs/{run_id}/summary.md", response_class=PlainTextResponse)
def engineering_summary(run_id: str, service: EngineeringEvidenceService = Depends(get_engineering_service)) -> str:
    try:
        return service.markdown_summary(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="engineering run not found") from exc

@app.post("/implementation/execute")
def execute_implementation(
    request: ImplementRequirementRequest,
    service: SecureImplementationService = Depends(get_implementation_service),
):
    return service.execute(request.requirement, request.engineer_signoff, request.approval_role)


@app.get("/implementation/runs/{run_id}/download")
def download_implementation(run_id: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    zip_path = settings.generated_workspace_root / f"{run_id}.zip"
    if not zip_path.exists():
        raise HTTPException(status_code=404, detail="implementation package not found")
    return FileResponse(zip_path, media_type="application/zip", filename=f"implementation-{run_id}.zip")

@app.get("/implementation/runs/{run_id}/preview", response_class=HTMLResponse)
def preview_implementation(run_id: str, settings: Settings = Depends(get_settings)) -> str:
    preview_root = settings.generated_workspace_root / run_id / "app" / "static"
    index_path = preview_root / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="generated UI preview not found")
    html = index_path.read_text(encoding="utf-8")
    html = html.replace('/static/styles.css', f'/implementation/runs/{run_id}/preview/static/styles.css')
    html = html.replace('/static/app.js', f'/implementation/runs/{run_id}/preview/static/app.js')
    return html


@app.get("/implementation/runs/{run_id}/preview/static/{asset_name}")
def preview_static_asset(run_id: str, asset_name: str, settings: Settings = Depends(get_settings)) -> FileResponse:
    allowed_assets = {"app.js", "styles.css"}
    if asset_name not in allowed_assets:
        raise HTTPException(status_code=404, detail="generated asset not found")
    asset_path = settings.generated_workspace_root / run_id / "app" / "static" / asset_name
    if not asset_path.exists():
        raise HTTPException(status_code=404, detail="generated asset not found")
    media_type = "text/css" if asset_name.endswith(".css") else "application/javascript"
    return FileResponse(asset_path, media_type=media_type)
