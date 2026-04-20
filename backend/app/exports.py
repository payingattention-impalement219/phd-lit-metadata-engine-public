from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import REPORTS_DIR
from .database import record_export
from .models import ExportResult, PaperRecord


EXPORT_COLUMNS = [
    "title",
    "abstract",
    "author_keywords",
    "indexed_keywords",
    "authors",
    "year",
    "doi",
    "pmid",
    "pmcid",
    "scopus_eid",
    "issn",
    "journal",
    "publisher",
    "publication_type",
    "language",
    "citation_count",
    "open_access_status",
    "source_databases",
    "source_urls",
    "is_preprint",
    "is_peer_reviewed_likely",
    "has_abstract",
    "has_keywords",
    "duplicate_group_id",
    "missing_fields",
]


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug[:80] or "metadata-export"


def _flatten(record: PaperRecord) -> dict[str, object]:
    data = record.model_dump()
    for key, value in list(data.items()):
        if isinstance(value, list):
            data[key] = "; ".join(str(item) for item in value)
        if isinstance(value, dict):
            data[key] = json.dumps(value, ensure_ascii=False)
    return {column: data.get(column, "") for column in EXPORT_COLUMNS}


def _ris(records: list[PaperRecord]) -> str:
    chunks: list[str] = []
    for record in records:
        chunks.append("TY  - JOUR")
        if record.title:
            chunks.append(f"TI  - {record.title}")
        if record.abstract:
            chunks.append(f"AB  - {record.abstract}")
        for author in record.authors:
            chunks.append(f"AU  - {author}")
        if record.year:
            chunks.append(f"PY  - {record.year}")
        if record.journal:
            chunks.append(f"JO  - {record.journal}")
        if record.doi:
            chunks.append(f"DO  - {record.doi}")
        for keyword in [*record.author_keywords, *record.indexed_keywords]:
            chunks.append(f"KW  - {keyword}")
        if record.source_urls:
            chunks.append(f"UR  - {record.source_urls[0]}")
        chunks.append("ER  - ")
        chunks.append("")
    return "\n".join(chunks)


def _bibtex_key(record: PaperRecord, idx: int) -> str:
    author = re.sub(r"[^A-Za-z]", "", record.authors[0].split()[-1]) if record.authors else "record"
    return f"{author}{record.year or 'nd'}{idx}"


def _bibtex_escape(text: str) -> str:
    return text.replace("{", "\\{").replace("}", "\\}")


def _bibtex(records: list[PaperRecord]) -> str:
    entries: list[str] = []
    for idx, record in enumerate(records, start=1):
        fields = {
            "title": record.title,
            "author": " and ".join(record.authors),
            "year": str(record.year or ""),
            "journal": record.journal,
            "doi": record.doi,
            "abstract": record.abstract,
            "keywords": ", ".join([*record.author_keywords, *record.indexed_keywords]),
            "url": record.source_urls[0] if record.source_urls else "",
        }
        lines = [f"@article{{{_bibtex_key(record, idx)},"]
        for key, value in fields.items():
            if value:
                lines.append(f"  {key} = {{{_bibtex_escape(value)}}},")
        lines.append("}")
        entries.append("\n".join(lines))
    return "\n\n".join(entries)


def export_records(job_id: str, records: list[PaperRecord], fmt: str) -> ExportResult:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{_slug(job_id)}-{timestamp}.{fmt}"
    path = REPORTS_DIR / filename

    if fmt == "xlsx":
        pd.DataFrame([_flatten(record) for record in records]).to_excel(path, index=False)
    elif fmt == "csv":
        pd.DataFrame([_flatten(record) for record in records]).to_csv(path, index=False)
    elif fmt == "txt":
        path.write_text(
            "\n\n".join(
                f"{record.title}\n{record.journal} ({record.year or 'n.d.'})\nDOI: {record.doi or 'n/a'}\n\n{record.abstract}"
                for record in records
            ),
            encoding="utf-8",
        )
    elif fmt == "jsonl":
        path.write_text("\n".join(record.model_dump_json() for record in records), encoding="utf-8")
    elif fmt == "ris":
        path.write_text(_ris(records), encoding="utf-8")
    elif fmt == "bib":
        path.write_text(_bibtex(records), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported export format: {fmt}")

    record_export(job_id, filename, str(path), fmt, len(records))
    return ExportResult(filename=filename, path=str(path), download_url=f"/api/exports/download/{filename}", record_count=len(records))

