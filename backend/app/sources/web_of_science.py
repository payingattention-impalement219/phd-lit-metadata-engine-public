from __future__ import annotations

from ..config import settings
from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient


class WebOfScienceClient(SourceClient):
    source_name = SourceName.web_of_science
    requires_key = True

    def configured(self) -> bool:
        # Clarivate has multiple Web of Science API products with different endpoints.
        # Keep this import/manual until a concrete endpoint entitlement is implemented.
        return False

    def unavailable_message(self) -> str:
        return (
            "Direct Web of Science support depends on your Clarivate product/API entitlement. "
            "Use RIS/BibTeX/CSV imports unless WEB_OF_SCIENCE_API_KEY and endpoint entitlement are configured."
        )

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        # Clarivate exposes several API products with different endpoints and schemas.
        # Keep this connector explicit rather than guessing the user's entitlement.
        return []
