from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urlencode

from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, clean_text, unique, year_from_date


class ArxivClient(SourceClient):
    source_name = SourceName.arxiv
    request_delay_seconds = 3.1

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        params = urlencode(
            {
                "search_query": f"all:{request.query}",
                "start": 0,
                "max_results": min(request.max_results_per_source, 100),
                "sortBy": "submittedDate",
                "sortOrder": "descending",
            }
        )
        text = await self.get_text(f"https://export.arxiv.org/api/query?{params}")
        root = ET.fromstring(text)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
        records: list[PaperRecord] = []
        for entry in root.findall("atom:entry", ns):
            authors = [clean_text(author.findtext("atom:name", default="", namespaces=ns)) for author in entry.findall("atom:author", ns)]
            categories = [category.attrib.get("term", "") for category in entry.findall("atom:category", ns)]
            arxiv_id = clean_text(entry.findtext("atom:id", default="", namespaces=ns))
            doi = clean_text(entry.findtext("arxiv:doi", default="", namespaces=ns))
            records.append(
                PaperRecord(
                    title=clean_text(entry.findtext("atom:title", default="", namespaces=ns)),
                    abstract=clean_text(entry.findtext("atom:summary", default="", namespaces=ns)),
                    indexed_keywords=unique(categories),
                    authors=unique(authors),
                    year=year_from_date(entry.findtext("atom:published", default="", namespaces=ns)),
                    doi=doi,
                    journal="arXiv",
                    publication_type="preprint",
                    source_databases=["arxiv"],
                    source_urls=unique([arxiv_id]),
                    is_preprint=True,
                    raw_ids={"arxiv": arxiv_id.rsplit("/", 1)[-1]},
                ).finalize_flags()
            )
        return _filter_years(records, request)


def _filter_years(records: list[PaperRecord], request: SearchRequest) -> list[PaperRecord]:
    output = []
    for record in records:
        if request.start_year and record.year and record.year < request.start_year:
            continue
        if request.end_year and record.year and record.year > request.end_year:
            continue
        output.append(record)
    return output
