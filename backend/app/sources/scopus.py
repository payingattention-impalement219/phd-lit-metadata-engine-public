from __future__ import annotations

import httpx

from ..config import settings
from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, SourceError, clean_text, unique, year_from_date


class ScopusClient(SourceClient):
    source_name = SourceName.scopus
    requires_key = True
    request_delay_seconds = 0.5

    def configured(self) -> bool:
        return bool(settings.elsevier_api_key)

    def unavailable_message(self) -> str:
        return "Scopus requires ELSEVIER_API_KEY, and may also require institutional access."

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        if not self.configured():
            return []
        headers = {"X-ELS-APIKey": settings.elsevier_api_key, "Accept": "application/json"}
        if settings.elsevier_inst_token:
            headers["X-ELS-Insttoken"] = settings.elsevier_inst_token

        query = request.query.strip()
        if request.start_year:
            query = f"{query} AND PUBYEAR > {request.start_year - 1}"
        if request.end_year:
            query = f"{query} AND PUBYEAR < {request.end_year + 1}"

        try:
            data = await self.get_json(
                "https://api.elsevier.com/content/search/scopus",
                params={"query": query, "count": min(request.max_results_per_source, 25)},
                headers=headers,
            )
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 403:
                raise SourceError(
                    "Scopus rejected the request. Check that ELSEVIER_API_KEY is valid and that your institution/API key "
                    "has Scopus Search API entitlement. Some accounts also need ELSEVIER_INST_TOKEN."
                ) from exc
            raise
        entries = data.get("search-results", {}).get("entry", [])
        records: list[PaperRecord] = []
        for item in entries:
            eid = clean_text(item.get("eid"))
            doi = clean_text(item.get("prism:doi"))
            records.append(
                PaperRecord(
                    title=clean_text(item.get("dc:title")),
                    abstract=clean_text(item.get("dc:description")),
                    authors=unique([item.get("dc:creator", "")]),
                    year=year_from_date(item.get("prism:coverDate")),
                    doi=doi,
                    scopus_eid=eid,
                    issn=clean_text(item.get("prism:issn") or item.get("prism:eIssn")),
                    journal=clean_text(item.get("prism:publicationName")),
                    publisher=clean_text(item.get("dc:publisher")),
                    publication_type=clean_text(item.get("subtypeDescription")),
                    citation_count=int(item["citedby-count"]) if str(item.get("citedby-count", "")).isdigit() else None,
                    source_databases=["scopus"],
                    source_urls=unique([link.get("@href", "") for link in item.get("link", []) if isinstance(link, dict)]),
                    raw_ids={"scopus": eid},
                    raw_record=item,
                ).finalize_flags()
            )
        return records
