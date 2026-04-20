from __future__ import annotations

from ..config import settings
from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, clean_text, unique, year_from_date


class CoreClient(SourceClient):
    source_name = SourceName.core
    requires_key = True
    request_delay_seconds = 1.0

    def configured(self) -> bool:
        return bool(settings.core_api_key)

    def unavailable_message(self) -> str:
        return "CORE requires CORE_API_KEY in .env."

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        if not self.configured():
            return []
        data = await self.get_json(
            "https://api.core.ac.uk/v3/search/works",
            params={"q": request.query, "limit": request.max_results_per_source},
            headers={"Authorization": f"Bearer {settings.core_api_key}"},
        )
        items = data.get("results", data if isinstance(data, list) else [])
        records: list[PaperRecord] = []
        for item in items:
            records.append(
                PaperRecord(
                    title=clean_text(item.get("title")),
                    abstract=clean_text(item.get("abstract")),
                    author_keywords=unique(item.get("topics", []) or []),
                    authors=unique([author.get("name", author) if isinstance(author, dict) else str(author) for author in item.get("authors", [])]),
                    year=year_from_date(item.get("publishedDate") or item.get("yearPublished")),
                    doi=clean_text(item.get("doi")),
                    journal=clean_text(item.get("journal")),
                    publisher=clean_text(item.get("publisher")),
                    publication_type=clean_text(item.get("documentType")),
                    open_access_status="open",
                    source_databases=["core"],
                    source_urls=unique([item.get("downloadUrl", ""), item.get("sourceFulltextUrls", [""])[0] if item.get("sourceFulltextUrls") else ""]),
                    is_preprint="preprint" in clean_text(item.get("documentType")).lower(),
                    raw_ids={"core": clean_text(item.get("id"))},
                    raw_record=item,
                ).finalize_flags()
            )
        return records
