from __future__ import annotations

from ..config import settings
from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, clean_text, first, unique, year_from_date


class CrossrefClient(SourceClient):
    source_name = SourceName.crossref
    request_delay_seconds = 0.2

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        filters = ["type:journal-article"]
        if request.start_year:
            filters.append(f"from-pub-date:{request.start_year}-01-01")
        if request.end_year:
            filters.append(f"until-pub-date:{request.end_year}-12-31")
        headers = {}
        if settings.contact_email:
            headers["User-Agent"] = f"phd-lit-metadata-engine/0.1 (mailto:{settings.contact_email})"
        data = await self.get_json(
            "https://api.crossref.org/works",
            params={
                "query.bibliographic": request.query,
                "rows": request.max_results_per_source,
                "filter": ",".join(filters),
            },
            headers=headers,
        )
        records: list[PaperRecord] = []
        for item in data.get("message", {}).get("items", []):
            authors = [
                " ".join(part for part in [author.get("given", ""), author.get("family", "")] if part)
                for author in item.get("author", [])
            ]
            date_parts = item.get("published-print", item.get("published-online", item.get("created", {}))).get("date-parts", [[]])
            year = date_parts[0][0] if date_parts and date_parts[0] else year_from_date(item.get("published"))
            records.append(
                PaperRecord(
                    title=first(item.get("title")),
                    abstract=clean_text(item.get("abstract")),
                    authors=unique(authors),
                    year=year,
                    doi=clean_text(item.get("DOI")),
                    issn="; ".join(item.get("ISSN", []) or []),
                    journal=first(item.get("container-title")),
                    publisher=clean_text(item.get("publisher")),
                    publication_type=clean_text(item.get("type")),
                    citation_count=item.get("is-referenced-by-count"),
                    source_databases=["crossref"],
                    source_urls=unique([item.get("URL", "")]),
                    is_preprint=clean_text(item.get("subtype")).lower() == "preprint",
                    raw_ids={"crossref": clean_text(item.get("DOI"))},
                    raw_record=item,
                ).finalize_flags()
            )
        return records
