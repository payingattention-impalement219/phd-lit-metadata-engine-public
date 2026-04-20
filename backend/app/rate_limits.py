from __future__ import annotations

from dataclasses import dataclass

from .models import SourceName


@dataclass(frozen=True)
class RateLimitInfo:
    note: str
    recommended_delay_seconds: float
    daily_limit_note: str = ""


RATE_LIMITS: dict[SourceName, RateLimitInfo] = {
    SourceName.pubmed: RateLimitInfo(
        note="NCBI E-utilities: 3 requests/second without an API key; up to 10 requests/second with NCBI_API_KEY.",
        recommended_delay_seconds=0.34,
        daily_limit_note="NCBI may ask high-volume jobs to run outside US business hours.",
    ),
    SourceName.europe_pmc: RateLimitInfo(
        note="Europe PMC does not publish a simple fixed metadata-search quota in the REST docs; keep requests moderate and back off on 429/503.",
        recommended_delay_seconds=0.25,
    ),
    SourceName.openalex: RateLimitInfo(
        note="OpenAlex documents 10 requests/second and 100,000 requests/day for authenticated use; include OPENALEX_API_KEY where available.",
        recommended_delay_seconds=0.11,
        daily_limit_note="100,000 requests/day documented for authenticated API use.",
    ),
    SourceName.crossref: RateLimitInfo(
        note="Crossref uses dynamic rate limits and returns X-Rate-Limit headers; contact email/User-Agent puts clients in the polite pool.",
        recommended_delay_seconds=0.2,
    ),
    SourceName.semantic_scholar: RateLimitInfo(
        note="Semantic Scholar metadata search uses the public/free bulk endpoint with token pagination; SEMANTIC_SCHOLAR_API_KEY improves steadiness under rate limits.",
        recommended_delay_seconds=1.25,
    ),
    SourceName.doaj: RateLimitInfo(
        note="DOAJ public API rate limits are modest; keep to about 2 requests/second and back off on 429.",
        recommended_delay_seconds=0.55,
    ),
    SourceName.core: RateLimitInfo(
        note="CORE requires CORE_API_KEY and applies account/key-specific limits; treat response headers and 429 as authoritative.",
        recommended_delay_seconds=1.0,
    ),
    SourceName.scopus: RateLimitInfo(
        note="Scopus requires Elsevier credentials; quota and throttle behavior are key/product-entitlement specific in the Elsevier developer portal.",
        recommended_delay_seconds=0.5,
    ),
    SourceName.web_of_science: RateLimitInfo(
        note="Web of Science direct API limits depend on the Clarivate product and entitlement; this app currently recommends export/import.",
        recommended_delay_seconds=1.0,
    ),
    SourceName.ieee_xplore: RateLimitInfo(
        note="IEEE Xplore limits are shown per API key in the developer portal; configure requests according to the active key quota.",
        recommended_delay_seconds=0.11,
        daily_limit_note="Some IEEE keys have daily quotas; check the IEEE developer portal before high-volume runs.",
    ),
    SourceName.acm_digital_library: RateLimitInfo(
        note="ACM Digital Library is manual/export-only in this app; follow ACM portal limits when searching there.",
        recommended_delay_seconds=0.0,
    ),
    SourceName.arxiv: RateLimitInfo(
        note="arXiv asks API users to make no more than one request every three seconds.",
        recommended_delay_seconds=3.1,
    ),
    SourceName.medrxiv: RateLimitInfo(
        note="medRxiv API does not publish a simple global quota in the endpoint docs; keep requests moderate and retry later on 429/503.",
        recommended_delay_seconds=1.0,
    ),
    SourceName.biorxiv: RateLimitInfo(
        note="bioRxiv API does not publish a simple global quota in the endpoint docs; keep requests moderate and retry later on 429/503.",
        recommended_delay_seconds=1.0,
    ),
}


def get_rate_limit_info(source_name: SourceName) -> RateLimitInfo:
    return RATE_LIMITS.get(source_name, RateLimitInfo(note="No rate-limit guidance configured.", recommended_delay_seconds=0.5))
