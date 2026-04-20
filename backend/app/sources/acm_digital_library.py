from __future__ import annotations

from ..models import PaperRecord, SearchRequest, SourceName
from .base import SourceClient


class AcmDigitalLibraryClient(SourceClient):
    source_name = SourceName.acm_digital_library
    requires_key = False

    def configured(self) -> bool:
        return False

    def unavailable_message(self) -> str:
        return (
            "ACM Digital Library does not provide a general public metadata search API for this app. "
            "Run the search in ACM DL, export RIS/BibTeX/CSV, then import or analyze the exported metadata."
        )

    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        return []

