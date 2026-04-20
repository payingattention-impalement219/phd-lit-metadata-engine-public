from __future__ import annotations

import asyncio

import httpx

from ..config import settings
from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, SourceError, clean_text, unique


SEMANTIC_SCHOLAR_FIELDS = (
    "paperId,title,abstract,authors,year,externalIds,venue,journal,citationCount,url,"
    "publicationTypes,publicationDate,fieldsOfStudy,isOpenAccess"
)
SEMANTIC_SCHOLAR_BULK_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"


class SemanticScholarClient(SourceClient):
    source_name = SourceName.semantic_scholar
    request_delay_seconds = 1.25
    http_429_retries = 0
    max_rate_limit_retries = 2

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        headers = self._headers()
        items = await self._bulk_search(request, headers=headers)
        return [self._record_from_item(item) for item in items]

    def _headers(self) -> dict[str, str]:
        headers = {}
        if settings.semantic_scholar_api_key:
            headers["x-api-key"] = settings.semantic_scholar_api_key
        return headers

    async def _bulk_search(self, request: SearchRequest, *, headers: dict[str, str]) -> list[dict[str, object]]:
        max_results = request.max_results_per_source
        params: dict[str, object] = {
            "query": request.query,
            "fields": SEMANTIC_SCHOLAR_FIELDS,
            "limit": min(max_results, 1000),
        }
        items: list[dict[str, object]] = []

        while True:
            data = await self._get_search_results(url=SEMANTIC_SCHOLAR_BULK_URL, params=params, headers=headers)
            page = data.get("data", [])
            if isinstance(page, list):
                items.extend([item for item in page if isinstance(item, dict)])

            if len(items) >= max_results:
                return items[:max_results]

            token = data.get("token")
            if not token:
                return items
            params["token"] = token

    def _record_from_item(self, item: dict[str, object]) -> PaperRecord:
        external = item.get("externalIds", {}) or {}
        journal = item.get("journal") or {}
        pub_types = item.get("publicationTypes") or []
        authors = item.get("authors") or []
        fields_of_study = item.get("fieldsOfStudy") or []

        if not isinstance(external, dict):
            external = {}
        if not isinstance(journal, dict):
            journal = {}
        if not isinstance(pub_types, list):
            pub_types = []
        if not isinstance(authors, list):
            authors = []
        if not isinstance(fields_of_study, list):
            fields_of_study = []

        return PaperRecord(
            title=clean_text(item.get("title")),
            abstract=clean_text(item.get("abstract")),
            indexed_keywords=unique(fields_of_study),
            authors=unique([author.get("name", "") for author in authors if isinstance(author, dict)]),
            year=item.get("year"),
            doi=clean_text(external.get("DOI")),
            pmid=clean_text(external.get("PubMed")),
            pmcid=clean_text(external.get("PubMedCentral")),
            journal=clean_text(journal.get("name") or item.get("venue")),
            publication_type="; ".join(clean_text(kind) for kind in pub_types if clean_text(kind)),
            citation_count=item.get("citationCount"),
            open_access_status="open" if item.get("isOpenAccess") else "",
            source_databases=["semantic_scholar"],
            source_urls=unique([item.get("url", "")]),
            is_preprint=any("preprint" in clean_text(kind).lower() for kind in pub_types),
            raw_ids={"semantic_scholar": clean_text(item.get("paperId"))},
            raw_record=item,
        ).finalize_flags()

    async def _get_search_results(self, *, url: str, params: dict[str, object], headers: dict[str, str]) -> dict[str, object]:
        for attempt in range(self.max_rate_limit_retries + 1):
            try:
                return await self.get_json(
                    url,
                    params=params,
                    headers=headers,
                )
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 429 or attempt >= self.max_rate_limit_retries:
                    if exc.response.status_code == 429:
                        raise SourceError(
                            "Semantic Scholar is free for most metadata searches, but the public unauthenticated pool "
                            "is rate-limited. The app retried and still hit the limit. Retry after a short wait, reduce "
                            "the number of custom strings, or add the optional SEMANTIC_SCHOLAR_API_KEY for steadier throughput."
                        ) from exc
                    raise
                await asyncio.sleep(self._retry_delay(exc.response, attempt))
        return {}

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), 30.0)
        return min(2.0 * (attempt + 1), 8.0)
