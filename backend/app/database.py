from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from .config import settings
from .config import PROJECT_DIR
from .models import JobStatus, JobSummary, PaperRecord


def _db_path() -> Path:
    path = settings.database_path
    if not path.is_absolute():
        path = PROJECT_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                query TEXT NOT NULL,
                request_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                total_records INTEGER NOT NULL DEFAULT 0,
                deduped_records INTEGER NOT NULL DEFAULT 0,
                source_counts_json TEXT NOT NULL DEFAULT '{}',
                errors_json TEXT NOT NULL DEFAULT '{}',
                message TEXT NOT NULL DEFAULT '',
                active_source TEXT NOT NULL DEFAULT '',
                active_query TEXT NOT NULL DEFAULT '',
                completed_steps INTEGER NOT NULL DEFAULT 0,
                total_steps INTEGER NOT NULL DEFAULT 0,
                progress_percent INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                dedupe_key TEXT NOT NULL,
                record_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES jobs(id)
            );

            CREATE TABLE IF NOT EXISTS exports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                path TEXT NOT NULL,
                format TEXT NOT NULL,
                record_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        _ensure_job_columns(con)


def _ensure_job_columns(con: sqlite3.Connection) -> None:
    existing = {row["name"] for row in con.execute("PRAGMA table_info(jobs)").fetchall()}
    columns = {
        "active_source": "TEXT NOT NULL DEFAULT ''",
        "active_query": "TEXT NOT NULL DEFAULT ''",
        "completed_steps": "INTEGER NOT NULL DEFAULT 0",
        "total_steps": "INTEGER NOT NULL DEFAULT 0",
        "progress_percent": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, definition in columns.items():
        if name not in existing:
            con.execute(f"ALTER TABLE jobs ADD COLUMN {name} {definition}")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(job: JobSummary, request_json: str) -> None:
    with connect() as con:
        con.execute(
            """
            INSERT INTO jobs (
                id, status, query, request_json, created_at, updated_at,
                total_records, deduped_records, source_counts_json, errors_json, message,
                active_source, active_query, completed_steps, total_steps, progress_percent
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job.id,
                job.status.value,
                job.query,
                request_json,
                job.created_at.isoformat(),
                job.updated_at.isoformat(),
                job.total_records,
                job.deduped_records,
                json.dumps(job.source_counts),
                json.dumps(job.errors),
                job.message,
                job.active_source,
                job.active_query,
                job.completed_steps,
                job.total_steps,
                job.progress_percent,
            ),
        )


def update_job(job: JobSummary) -> None:
    with connect() as con:
        con.execute(
            """
            UPDATE jobs
            SET status = ?, updated_at = ?, total_records = ?, deduped_records = ?,
                source_counts_json = ?, errors_json = ?, message = ?,
                active_source = ?, active_query = ?, completed_steps = ?,
                total_steps = ?, progress_percent = ?
            WHERE id = ?
            """,
            (
                job.status.value,
                job.updated_at.isoformat(),
                job.total_records,
                job.deduped_records,
                json.dumps(job.source_counts),
                json.dumps(job.errors),
                job.message,
                job.active_source,
                job.active_query,
                job.completed_steps,
                job.total_steps,
                job.progress_percent,
                job.id,
            ),
        )


def save_records(job_id: str, records: list[PaperRecord]) -> None:
    created_at = utc_now()
    with connect() as con:
        con.execute("DELETE FROM records WHERE job_id = ?", (job_id,))
        con.executemany(
            "INSERT INTO records (job_id, dedupe_key, record_json, created_at) VALUES (?, ?, ?, ?)",
            [
                (
                    job_id,
                    record.duplicate_group_id or record.doi or record.pmid or record.title.lower(),
                    record.model_dump_json(),
                    created_at,
                )
                for record in records
            ],
        )


def get_job(job_id: str) -> JobSummary | None:
    with connect() as con:
        row = con.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        return None
    return JobSummary(
        id=row["id"],
        status=JobStatus(row["status"]),
        query=row["query"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        total_records=row["total_records"],
        deduped_records=row["deduped_records"],
        source_counts=json.loads(row["source_counts_json"]),
        errors=json.loads(row["errors_json"]),
        message=row["message"],
        active_source=row["active_source"],
        active_query=row["active_query"],
        completed_steps=row["completed_steps"],
        total_steps=row["total_steps"],
        progress_percent=row["progress_percent"],
    )


def list_jobs(limit: int = 20) -> list[JobSummary]:
    with connect() as con:
        rows = con.execute("SELECT id FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [job for row in rows if (job := get_job(row["id"]))]


def list_records(job_id: str) -> list[tuple[int, PaperRecord]]:
    with connect() as con:
        rows = con.execute("SELECT id, record_json FROM records WHERE job_id = ? ORDER BY id", (job_id,)).fetchall()
    return [(row["id"], PaperRecord.model_validate_json(row["record_json"])) for row in rows]


def record_export(job_id: str, filename: str, path: str, fmt: str, record_count: int) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO exports (job_id, filename, path, format, record_count, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (job_id, filename, path, fmt, record_count, utc_now()),
        )
