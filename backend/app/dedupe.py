from __future__ import annotations

import hashlib
import re
from collections import defaultdict

from .models import PaperRecord

try:
    from rapidfuzz import fuzz
except Exception:  # pragma: no cover - fallback for minimal environments
    fuzz = None


def normalize_doi(doi: str) -> str:
    doi = doi.strip().lower()
    doi = re.sub(r"^https?://(dx\.)?doi\.org/", "", doi)
    return doi


def normalize_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title.strip().lower())
    title = re.sub(r"[^a-z0-9 ]", "", title)
    return title


def merge_records(records: list[PaperRecord]) -> PaperRecord:
    base = records[0].model_copy(deep=True)
    for record in records[1:]:
        for field in (
            "title",
            "abstract",
            "doi",
            "pmid",
            "pmcid",
            "scopus_eid",
            "issn",
            "journal",
            "publisher",
            "publication_type",
            "language",
            "open_access_status",
        ):
            if not getattr(base, field) and getattr(record, field):
                setattr(base, field, getattr(record, field))
        if base.year is None and record.year is not None:
            base.year = record.year
        if base.citation_count is None or (record.citation_count or 0) > (base.citation_count or 0):
            base.citation_count = record.citation_count
        for list_field in ("author_keywords", "indexed_keywords", "authors", "source_databases", "source_urls"):
            merged = list(dict.fromkeys([*getattr(base, list_field), *getattr(record, list_field)]))
            setattr(base, list_field, merged)
        base.raw_ids.update(record.raw_ids)
        base.is_preprint = base.is_preprint or record.is_preprint
    return base.finalize_flags()


def _record_key(record: PaperRecord) -> str:
    if record.doi:
        return f"doi:{normalize_doi(record.doi)}"
    if record.pmid:
        return f"pmid:{record.pmid}"
    if record.pmcid:
        return f"pmcid:{record.pmcid}"
    if record.scopus_eid:
        return f"scopus:{record.scopus_eid}"
    title = normalize_title(record.title)
    if title and record.year:
        return f"title-year:{title}:{record.year}"
    return f"hash:{hashlib.sha1(record.model_dump_json().encode()).hexdigest()}"


def dedupe_records(records: list[PaperRecord]) -> list[PaperRecord]:
    exact_groups: dict[str, list[PaperRecord]] = defaultdict(list)
    for record in records:
        exact_groups[_record_key(record)].append(record.finalize_flags())

    merged = [merge_records(group) for group in exact_groups.values()]
    output: list[PaperRecord] = []
    used: set[int] = set()

    for idx, record in enumerate(merged):
        if idx in used:
            continue
        group = [record]
        title = normalize_title(record.title)
        for other_idx in range(idx + 1, len(merged)):
            if other_idx in used:
                continue
            other = merged[other_idx]
            if not title or not other.title or record.year != other.year:
                continue
            other_title = normalize_title(other.title)
            score = fuzz.ratio(title, other_title) if fuzz else (100 if title == other_title else 0)
            if score >= 94:
                group.append(other)
                used.add(other_idx)
        duplicate_group_id = hashlib.sha1(_record_key(group[0]).encode()).hexdigest()[:12]
        combined = merge_records(group)
        combined.duplicate_group_id = duplicate_group_id
        output.append(combined.finalize_flags())

    return output

