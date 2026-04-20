from __future__ import annotations

from ..models import SourceName, SourceStatus
from ..rate_limits import get_rate_limit_info
from .base import SourceClient
from .acm_digital_library import AcmDigitalLibraryClient
from .arxiv import ArxivClient
from .biorxiv import BiorxivClient, MedrxivClient
from .core import CoreClient
from .crossref import CrossrefClient
from .doaj import DoajClient
from .europe_pmc import EuropePmcClient
from .openalex import OpenAlexClient
from .pubmed import PubMedClient
from .scopus import ScopusClient
from .semantic_scholar import SemanticScholarClient
from .web_of_science import WebOfScienceClient
from .ieee_xplore import IeeeXploreClient


CLIENTS: dict[SourceName, type[SourceClient]] = {
    SourceName.pubmed: PubMedClient,
    SourceName.europe_pmc: EuropePmcClient,
    SourceName.openalex: OpenAlexClient,
    SourceName.crossref: CrossrefClient,
    SourceName.semantic_scholar: SemanticScholarClient,
    SourceName.doaj: DoajClient,
    SourceName.core: CoreClient,
    SourceName.scopus: ScopusClient,
    SourceName.web_of_science: WebOfScienceClient,
    SourceName.ieee_xplore: IeeeXploreClient,
    SourceName.acm_digital_library: AcmDigitalLibraryClient,
    SourceName.arxiv: ArxivClient,
    SourceName.medrxiv: MedrxivClient,
    SourceName.biorxiv: BiorxivClient,
}


def get_client(source_name: SourceName) -> SourceClient:
    return CLIENTS[source_name]()


def list_source_statuses() -> list[SourceStatus]:
    statuses: list[SourceStatus] = []
    for name, client_cls in CLIENTS.items():
        client = client_cls()
        configured = client.configured()
        rate_limit = get_rate_limit_info(name)
        statuses.append(
            SourceStatus(
                name=name,
                enabled=True,
                available=configured,
                requires_key=client.requires_key,
                configured=configured,
                message="" if configured else client.unavailable_message(),
                rate_limit_note=rate_limit.note,
                recommended_delay_seconds=rate_limit.recommended_delay_seconds,
                daily_limit_note=rate_limit.daily_limit_note,
            )
        )
    return statuses
