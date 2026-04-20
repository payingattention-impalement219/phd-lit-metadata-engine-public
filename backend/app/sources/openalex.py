from __future__ import annotations

from ..config import settings
from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, abstract_from_inverted_index, clean_text, unique, year_from_date


class OpenAlexClient(SourceClient):
    source_name = SourceName.openalex
    request_delay_seconds = 0.11

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        filters = []
        if request.start_year:
            filters.append(f"from_publication_date:{request.start_year}-01-01")
        if request.end_year:
            filters.append(f"to_publication_date:{request.end_year}-12-31")
        params = {
            "search": request.query,
            "per-page": request.max_results_per_source,
        }
        if filters:
            params["filter"] = ",".join(filters)
        if settings.contact_email:
            params["mailto"] = settings.contact_email
        if settings.openalex_api_key:
            params["api_key"] = settings.openalex_api_key

        data = await self.get_json("https://api.openalex.org/works", params=params)
        records: list[PaperRecord] = []
        for item in data.get("results", []):
            doi = clean_text(item.get("doi"))
            if doi.startswith("https://doi.org/"):
                doi = doi.removeprefix("https://doi.org/")
            authors = [
                authorship.get("author", {}).get("display_name", "")
                for authorship in item.get("authorships", [])
            ]
            concepts = [concept.get("display_name", "") for concept in item.get("concepts", [])[:12]]
            location = item.get("primary_location") or {}
            source = location.get("source") or {}
            oa = item.get("open_access") or {}
            records.append(
                PaperRecord(
                    title=clean_text(item.get("title") or item.get("display_name")),
                    abstract=abstract_from_inverted_index(item.get("abstract_inverted_index")),
                    indexed_keywords=unique(concepts),
                    authors=unique(authors),
                    year=item.get("publication_year") or year_from_date(item.get("publication_date")),
                    doi=doi,
                    journal=clean_text(source.get("display_name")),
                    issn="; ".join(source.get("issn", []) or []),
                    publisher=clean_text(item.get("host_venue", {}).get("publisher")),
                    publication_type=clean_text(item.get("type")),
                    citation_count=item.get("cited_by_count"),
                    open_access_status=clean_text(oa.get("oa_status")),
                    source_databases=["openalex"],
                    source_urls=unique([item.get("id", ""), item.get("doi", ""), location.get("landing_page_url", "")]),
                    is_preprint=clean_text(item.get("type")).lower() == "preprint",
                    raw_ids={"openalex": clean_text(item.get("id"))},
                    raw_record=item,
                ).finalize_flags()
            )
        return records
