from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


PLACEHOLDER_MARKERS = (
    "your ",
    "related term",
    "related method",
    "specific subtopic",
    "second concept",
)


class SourceName(str, Enum):
    pubmed = "pubmed"
    europe_pmc = "europe_pmc"
    openalex = "openalex"
    crossref = "crossref"
    semantic_scholar = "semantic_scholar"
    doaj = "doaj"
    core = "core"
    scopus = "scopus"
    web_of_science = "web_of_science"
    ieee_xplore = "ieee_xplore"
    acm_digital_library = "acm_digital_library"
    arxiv = "arxiv"
    medrxiv = "medrxiv"
    biorxiv = "biorxiv"


class PaperRecord(BaseModel):
    title: str = ""
    abstract: str = ""
    author_keywords: list[str] = Field(default_factory=list)
    indexed_keywords: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""
    scopus_eid: str = ""
    issn: str = ""
    journal: str = ""
    publisher: str = ""
    publication_type: str = ""
    language: str = ""
    citation_count: int | None = None
    open_access_status: str = ""
    source_databases: list[str] = Field(default_factory=list)
    source_urls: list[str] = Field(default_factory=list)
    is_preprint: bool = False
    is_peer_reviewed_likely: bool = False
    has_abstract: bool = False
    has_keywords: bool = False
    duplicate_group_id: str = ""
    missing_fields: list[str] = Field(default_factory=list)
    raw_ids: dict[str, str] = Field(default_factory=dict)
    raw_record: dict[str, Any] = Field(default_factory=dict)

    def finalize_flags(self) -> "PaperRecord":
        self.has_abstract = bool(self.abstract.strip())
        self.has_keywords = bool(self.author_keywords or self.indexed_keywords)
        self.missing_fields = [
            field
            for field in ("title", "abstract", "doi", "journal", "year")
            if not getattr(self, field)
        ]
        source_names = {source.lower() for source in self.source_databases}
        pub_type = self.publication_type.lower()
        journalish = bool(self.journal and "preprint" not in self.journal.lower())
        self.is_preprint = self.is_preprint or "preprint" in pub_type or "preprint" in self.open_access_status.lower()
        self.is_peer_reviewed_likely = (
            not self.is_preprint
            and journalish
            and (
                "doaj" in source_names
                or "pubmed" in source_names
                or "scopus" in source_names
                or "web_of_science" in source_names
                or "journal" in pub_type
                or "article" in pub_type
                or "review" in pub_type
            )
        )
        return self


class SourceStatus(BaseModel):
    name: SourceName
    enabled: bool
    available: bool
    requires_key: bool = False
    configured: bool = True
    message: str = ""
    rate_limit_note: str = ""
    recommended_delay_seconds: float = 0.0
    daily_limit_note: str = ""


class SearchRequest(BaseModel):
    query: str
    query_strings: list[str] = Field(default_factory=list)
    source_queries: dict[SourceName, list[str]] = Field(default_factory=dict)
    keywords: list[str] = Field(default_factory=list)
    start_year: int | None = None
    end_year: int | None = None
    sources: list[SourceName] = Field(default_factory=list)
    max_results_per_source: int = Field(default=25, ge=1, le=200)
    language: str = ""
    publication_types: list[str] = Field(default_factory=list)
    require_abstract: bool = False
    require_keywords: bool = False
    include_preprints: bool = False

    def effective_queries(self, source_name: SourceName | None = None) -> list[str]:
        queries = [query.strip() for query in self.query_strings if query.strip()]
        if self.query.strip():
            queries.insert(0, self.query.strip())
        if source_name is not None:
            queries.extend(query.strip() for query in self.source_queries.get(source_name, []) if query.strip())
        return [query for query in dict.fromkeys(queries) if not is_placeholder_query(query)]


def is_placeholder_query(query: str) -> bool:
    normalized = query.lower()
    return any(marker in normalized for marker in PLACEHOLDER_MARKERS)


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class JobSummary(BaseModel):
    id: str
    status: JobStatus
    query: str
    created_at: datetime
    updated_at: datetime
    total_records: int = 0
    deduped_records: int = 0
    source_counts: dict[str, int] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
    message: str = ""
    active_source: str = ""
    active_query: str = ""
    completed_steps: int = 0
    total_steps: int = 0
    progress_percent: int = 0


class ExportRequest(BaseModel):
    job_id: str
    format: Literal["xlsx", "csv", "txt", "jsonl", "bib", "ris"]
    filtered_record_ids: list[int] = Field(default_factory=list)


class ExportResult(BaseModel):
    filename: str
    path: str
    download_url: str
    record_count: int


class NotebookStatus(BaseModel):
    notebook_path: str
    jupyter_available: bool
    vscode_available: bool
    jupyter_command: str = ""
    vscode_command: str = ""
    message: str = ""


class ApiSettingStatus(BaseModel):
    field: str
    env_name: str
    label: str
    required_for: list[str]
    help_text: str
    secret: bool = True
    configured: bool = False
    masked_value: str = ""


class ApiSettingsUpdate(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)
