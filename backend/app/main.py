from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import database
from .config import REPORTS_DIR, settings_status, update_env_settings
from .database import list_jobs, list_records
from .exports import export_records
from .harvest import dump_analysis_context, get_job, new_job, records_for_job, run_harvest
from .models import ApiSettingStatus, ApiSettingsUpdate, ExportRequest, SearchRequest
from .notebook_launcher import LOCAL_HOSTS, notebook_status, open_jupyter, open_vscode, write_context
from .sources.registry import list_source_statuses


app = FastAPI(title="PhD Literature Metadata Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    database.init_db()
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def ensure_local(request: Request) -> None:
    host = request.client.host if request.client else ""
    if host not in LOCAL_HOSTS:
        raise HTTPException(status_code=403, detail="Notebook launcher endpoints are local-only.")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sources/status")
def sources_status():
    return list_source_statuses()


@app.get("/api/settings/api-keys", response_model=list[ApiSettingStatus])
def api_key_status(request: Request):
    ensure_local(request)
    return settings_status()


@app.post("/api/settings/api-keys", response_model=list[ApiSettingStatus])
def update_api_keys(request: Request, update: ApiSettingsUpdate):
    ensure_local(request)
    update_env_settings(update.values)
    return settings_status()


@app.post("/api/search")
async def create_search(request: SearchRequest):
    job = new_job(request)
    asyncio.create_task(run_harvest(job.id, request))
    return job


@app.get("/api/jobs")
def jobs():
    return list_jobs()


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/api/jobs/{job_id}/records")
def job_records(job_id: str):
    if not get_job(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return records_for_job(job_id)


@app.post("/api/exports")
def export_job(request: ExportRequest):
    rows = list_records(request.job_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No records found for this job")
    if request.filtered_record_ids:
        allowed = set(request.filtered_record_ids)
        records = [record for row_id, record in rows if row_id in allowed]
    else:
        records = [record for _, record in rows]
    result = export_records(request.job_id, records, request.format)
    dump_analysis_context(request.job_id, result.path)
    return result


@app.get("/api/exports/download/{filename}")
def download_export(filename: str):
    path = REPORTS_DIR / Path(filename).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Export not found")
    return FileResponse(path, filename=path.name)


@app.get("/api/notebooks/status")
def get_notebook_status(request: Request):
    ensure_local(request)
    return notebook_status()


@app.post("/api/notebooks/open/jupyter")
def launch_jupyter(request: Request):
    ensure_local(request)
    try:
        return open_jupyter()
    except Exception as exc:
        return {"status": "unavailable", "message": f"Could not open Jupyter: {exc}"}


@app.post("/api/notebooks/open/vscode")
def launch_vscode(request: Request):
    ensure_local(request)
    try:
        return open_vscode()
    except Exception as exc:
        return {"status": "unavailable", "message": f"Could not open VS Code: {exc}"}


@app.post("/api/notebooks/export-and-open")
def export_then_open(request: Request, export_request: ExportRequest, target: str = "jupyter"):
    ensure_local(request)
    rows = list_records(export_request.job_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No records found for this job")
    records = [record for _, record in rows]
    result = export_records(export_request.job_id, records, export_request.format)
    write_context(export_request.job_id, result.path)
    try:
        launch = open_vscode() if target == "vscode" else open_jupyter()
    except Exception as exc:
        launch = {"status": "unavailable", "message": f"Export succeeded, but notebook launch failed: {exc}"}
    return {"export": result, "notebook": launch}
