from __future__ import annotations

from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, clean_text, unique, year_from_date


class EuropePmcClient(SourceClient):
    source_name = SourceName.europe_pmc
    request_delay_seconds = 0.25

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        query = request.query
        if request.start_year or request.end_year:
            start = request.start_year or 1800
            end = request.end_year or 3000
            query = f"({query}) AND FIRST_PDATE:[{start}-01-01 TO {end}-12-31]"

        data = await self.get_json(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={
                "query": query,
                "format": "json",
                "resultType": "core",
                "pageSize": request.max_results_per_source,
            },
        )
        records: list[PaperRecord] = []
        for item in data.get("resultList", {}).get("result", []):
            authors = [author.get("fullName", "") for author in item.get("authorList", {}).get("author", [])]
            keywords = item.get("keywordList", {}).get("keyword", [])
            pmid = clean_text(item.get("pmid"))
            pmcid = clean_text(item.get("pmcid"))
            doi = clean_text(item.get("doi"))
            url = item.get("fullTextUrlList", {}).get("fullTextUrl", [])
            urls = [entry.get("url", "") for entry in url if entry.get("url")]
            if pmid:
                urls.append(f"https://europepmc.org/article/MED/{pmid}")

            records.append(
                PaperRecord(
                    title=clean_text(item.get("title")),
                    abstract=clean_text(item.get("abstractText")),
                    author_keywords=unique(keywords),
                    authors=unique(authors),
                    year=year_from_date(item.get("firstPublicationDate")) or year_from_date(item.get("pubYear")),
                    doi=doi,
                    pmid=pmid,
                    pmcid=pmcid,
                    journal=clean_text(item.get("journalTitle")),
                    publisher=clean_text(item.get("publisher")),
                    publication_type=clean_text(item.get("pubType")),
                    citation_count=int(item["citedByCount"]) if str(item.get("citedByCount", "")).isdigit() else None,
                    open_access_status="open" if item.get("isOpenAccess") == "Y" else "",
                    source_databases=["europe_pmc"],
                    source_urls=unique(urls),
                    raw_ids={"europe_pmc": clean_text(item.get("id"))},
                    raw_record=item,
                ).finalize_flags()
            )
        return records
