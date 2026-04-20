from __future__ import annotations

from urllib.parse import quote

from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, clean_text, unique, year_from_date


class DoajClient(SourceClient):
    source_name = SourceName.doaj
    request_delay_seconds = 0.55

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        # DOAJ search supports a Lucene-style query in the URL path.
        url = f"https://doaj.org/api/search/articles/{quote(request.query)}"
        data = await self.get_json(url, params={"page": 1, "pageSize": request.max_results_per_source})
        records: list[PaperRecord] = []
        for item in data.get("results", []):
            bib = item.get("bibjson", {})
            identifiers = {identifier.get("type", ""): identifier.get("id", "") for identifier in bib.get("identifier", [])}
            journal = bib.get("journal", {})
            links = [link.get("url", "") for link in bib.get("link", [])]
            records.append(
                PaperRecord(
                    title=clean_text(bib.get("title")),
                    abstract=clean_text(bib.get("abstract")),
                    author_keywords=unique(bib.get("keywords", []) or []),
                    authors=unique([author.get("name", "") for author in bib.get("author", [])]),
                    year=year_from_date(bib.get("year")),
                    doi=clean_text(identifiers.get("doi")),
                    issn=clean_text(identifiers.get("eissn") or identifiers.get("pissn")),
                    journal=clean_text(journal.get("title")),
                    publisher=clean_text(journal.get("publisher")),
                    publication_type="journal-article",
                    open_access_status="open",
                    source_databases=["doaj"],
                    source_urls=unique(links),
                    raw_ids={"doaj": clean_text(item.get("id"))},
                    raw_record=item,
                ).finalize_flags()
            )
        return records
