from __future__ import annotations

import re
from datetime import date

from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient, clean_text, unique, year_from_date


class BiorxivClient(SourceClient):
    source_name = SourceName.biorxiv
    server = "biorxiv"
    request_delay_seconds = 1.0

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        return await _rxiv_search(self, request, self.server)


class MedrxivClient(SourceClient):
    source_name = SourceName.medrxiv
    server = "medrxiv"
    request_delay_seconds = 1.0

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        return await _rxiv_search(self, request, self.server)


async def _rxiv_search(client: SourceClient, request: SearchRequest, server: str) -> list[PaperRecord]:
    start_year = request.start_year or date.today().year - 2
    end_year = request.end_year or date.today().year
    url = f"https://api.biorxiv.org/details/{server}/{start_year}-01-01/{end_year}-12-31/0/json"
    data = await client.get_json(url)
    terms = _query_terms(request.query)
    records: list[PaperRecord] = []
    for item in data.get("collection", []):
        haystack = " ".join([clean_text(item.get("title")), clean_text(item.get("abstract"))]).lower()
        if terms and not any(term in haystack for term in terms):
            continue
        doi = clean_text(item.get("doi"))
        records.append(
            PaperRecord(
                title=clean_text(item.get("title")),
                abstract=clean_text(item.get("abstract")),
                authors=unique([item.strip() for item in clean_text(item.get("authors")).split(";")]),
                year=year_from_date(item.get("date")),
                doi=doi,
                journal=server,
                publication_type="preprint",
                source_databases=[server],
                source_urls=unique([f"https://doi.org/{doi}" if doi else ""]),
                is_preprint=True,
                raw_ids={server: doi},
                raw_record=item,
            ).finalize_flags()
        )
        if len(records) >= request.max_results_per_source:
            break
    return records


def _query_terms(query: str) -> list[str]:
    quoted = re.findall(r'"([^"]+)"', query.lower())
    bare = [
        token
        for token in re.findall(r"[a-z][a-z0-9-]{3,}", query.lower())
        if token not in {"and", "or", "not", "title", "abstract", "tiab", "mesh"}
    ]
    return list(dict.fromkeys([*quoted, *bare]))
