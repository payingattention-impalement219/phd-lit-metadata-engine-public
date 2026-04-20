from __future__ import annotations

from ..config import settings
from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, clean_text, unique, year_from_date


class IeeeXploreClient(SourceClient):
    source_name = SourceName.ieee_xplore
    requires_key = True
    request_delay_seconds = 0.11

    def configured(self) -> bool:
        return bool(settings.ieee_api_key)

    def unavailable_message(self) -> str:
        return "IEEE Xplore requires IEEE_API_KEY in .env."

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        if not self.configured():
            return []
        data = await self.get_json(
            "https://ieeexploreapi.ieee.org/api/v1/search/articles",
            params={
                "apikey": settings.ieee_api_key,
                "format": "json",
                "max_records": min(request.max_results_per_source, 200),
                "start_record": 1,
                "querytext": request.query,
                "start_year": request.start_year or "",
                "end_year": request.end_year or "",
            },
        )
        records: list[PaperRecord] = []
        for item in data.get("articles", []):
            doi = clean_text(item.get("doi"))
            records.append(
                PaperRecord(
                    title=clean_text(item.get("title")),
                    abstract=clean_text(item.get("abstract")),
                    author_keywords=unique(item.get("author_terms", {}).get("terms", []) if isinstance(item.get("author_terms"), dict) else []),
                    indexed_keywords=unique(item.get("index_terms", {}).get("terms", []) if isinstance(item.get("index_terms"), dict) else []),
                    authors=unique([author.get("full_name", "") for author in item.get("authors", {}).get("authors", [])] if isinstance(item.get("authors"), dict) else []),
                    year=year_from_date(item.get("publication_year")),
                    doi=doi,
                    issn=clean_text(item.get("issn")),
                    journal=clean_text(item.get("publication_title")),
                    publisher="IEEE",
                    publication_type=clean_text(item.get("content_type")),
                    citation_count=item.get("citing_paper_count"),
                    source_databases=["ieee_xplore"],
                    source_urls=unique([item.get("html_url", ""), f"https://doi.org/{doi}" if doi else ""]),
                    raw_ids={"ieee_xplore": clean_text(item.get("article_number"))},
                    raw_record=item,
                ).finalize_flags()
            )
        return records
