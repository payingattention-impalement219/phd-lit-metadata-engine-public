from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime, timezone

from . import database
from .dedupe import dedupe_records
from .models import JobStatus, JobSummary, PaperRecord, SearchRequest, SourceName
from .sources.registry import get_client


JOBS: dict[str, JobSummary] = {}
EXPECTED_SKIP_SOURCES = {SourceName.web_of_science, SourceName.acm_digital_library}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def new_job(request: SearchRequest) -> JobSummary:
    display_query = request.query or " | ".join(request.effective_queries()) or "source-specific search strings"
    selected_sources = _default_sources(request)
    total_steps = sum(len(request.effective_queries(source_name)) or 1 for source_name in selected_sources)
    job = JobSummary(
        id=str(uuid.uuid4()),
        status=JobStatus.queued,
        query=display_query,
        created_at=_now(),
        updated_at=_now(),
        total_steps=total_steps,
        message="Queued",
    )
    JOBS[job.id] = job
    database.create_job(job, request.model_dump_json())
    return job


def get_job(job_id: str) -> JobSummary | None:
    return JOBS.get(job_id) or database.get_job(job_id)


def _default_sources(request: SearchRequest) -> list[SourceName]:
    if request.sources:
        return request.sources
    return [
        SourceName.pubmed,
        SourceName.europe_pmc,
        SourceName.openalex,
        SourceName.crossref,
        SourceName.semantic_scholar,
        SourceName.doaj,
    ]


def _passes_filters(record: PaperRecord, request: SearchRequest) -> bool:
    if request.require_abstract and not record.has_abstract:
        return False
    if request.require_keywords and not record.has_keywords:
        return False
    if not request.include_preprints and record.is_preprint:
        return False
    if request.language and record.language and request.language.lower() != record.language.lower():
        return False
    if request.publication_types:
        publication_type = record.publication_type.lower()
        if publication_type and not any(kind.lower() in publication_type for kind in request.publication_types):
            return False
    return True


def _set_progress(job: JobSummary, *, completed_steps: int | None = None) -> None:
    if completed_steps is not None:
        job.completed_steps = completed_steps
    if job.total_steps:
        job.progress_percent = min(100, round((job.completed_steps / job.total_steps) * 100))


async def run_harvest(job_id: str, request: SearchRequest) -> None:
    job = get_job(job_id)
    if not job:
        return

    job.status = JobStatus.running
    job.updated_at = _now()
    job.message = "Harvesting metadata"
    JOBS[job_id] = job
    database.update_job(job)

    all_records: list[PaperRecord] = []
    selected_sources = _default_sources(request)
    has_any_queries = any(request.effective_queries(source_name) for source_name in selected_sources)
    if not has_any_queries:
        job.status = JobStatus.failed
        job.updated_at = _now()
        job.message = "No search strings were provided"
        JOBS[job_id] = job
        database.update_job(job)
        return
    job.total_steps = sum(len(request.effective_queries(source_name)) or 1 for source_name in selected_sources)
    _set_progress(job, completed_steps=0)
    database.update_job(job)

    completed_steps = 0
    for source_name in selected_sources:
        client = get_client(source_name)
        job.active_source = source_name.value
        if not client.configured():
            message = client.unavailable_message() or "Source is not configured."
            if source_name in EXPECTED_SKIP_SOURCES:
                job.message = f"Skipped {source_name.value}: import/manual source"
            else:
                job.errors[source_name.value] = message
                job.message = f"Skipped {source_name.value}: source is not configured"
            completed_steps += max(1, len(request.effective_queries(source_name)))
            job.active_query = ""
            _set_progress(job, completed_steps=completed_steps)
            job.updated_at = _now()
            database.update_job(job)
            continue
        source_total = 0
        queries = request.effective_queries(source_name)
        for query_text in queries:
            query_request = request.model_copy(update={"query": query_text, "query_strings": [], "source_queries": {}})
            job.active_query = query_text[:220]
            job.message = f"Searching {source_name.value}"
            job.updated_at = _now()
            JOBS[job_id] = job
            database.update_job(job)
            try:
                records = await client.search(query_request)
                filtered = [record for record in records if _passes_filters(record.finalize_flags(), request)]
                source_total += len(filtered)
                all_records.extend(filtered)
                job.total_records = len(all_records)
                job.source_counts[source_name.value] = source_total
                completed_steps += 1
                _set_progress(job, completed_steps=completed_steps)
                job.message = f"Fetched {len(filtered)} records from {source_name.value}"
                job.updated_at = _now()
                JOBS[job_id] = job
                database.update_job(job)
            except Exception as exc:
                error_key = f"{source_name.value}:{query_text[:48]}"
                job.errors[error_key] = str(exc)
                completed_steps += 1
                _set_progress(job, completed_steps=completed_steps)
                job.updated_at = _now()
                JOBS[job_id] = job
                database.update_job(job)
                await asyncio.sleep(0)

    deduped = dedupe_records(all_records)
    database.save_records(job_id, deduped)

    job.status = JobStatus.completed
    job.updated_at = _now()
    job.deduped_records = len(deduped)
    job.total_records = len(all_records)
    job.active_source = ""
    job.active_query = ""
    job.completed_steps = job.total_steps
    job.progress_percent = 100
    job.message = f"Completed with {len(deduped)} deduplicated records"
    JOBS[job_id] = job
    database.update_job(job)


def records_for_job(job_id: str) -> list[dict[str, object]]:
    rows = database.list_records(job_id)
    return [{"id": row_id, **record.model_dump()} for row_id, record in rows]


def dump_analysis_context(job_id: str, export_path: str | None = None) -> None:
    from .config import PROJECT_DIR

    context_path = PROJECT_DIR / "notebooks" / "analysis_context.json"
    context_path.write_text(
        json.dumps({"job_id": job_id, "export_path": export_path or "", "updated_at": _now().isoformat()}, indent=2),
        encoding="utf-8",
    )
