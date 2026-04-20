from __future__ import annotations

import asyncio
import re
from abc import ABC, abstractmethod
from html import unescape
from typing import Any

import httpx

from ..models import PaperRecord, SearchRequest, SourceName


class SourceError(RuntimeError):
    """Raised when a source fails in a controlled way."""


class SourceClient(ABC):
    source_name: SourceName
    requires_key: bool = False
    request_delay_seconds: float = 0.25
    http_429_retries: int = 2

    def __init__(self, timeout: float = 30.0) -> None:
        self.timeout = timeout

    @abstractmethod
    async def search(self, request: SearchRequest) -> list[PaperRecord]:
        """Return normalized paper metadata records."""

    def configured(self) -> bool:
        return True

    def unavailable_message(self) -> str:
        return ""

    async def get_json(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
        response = await self._get_with_backoff(url, params=params, headers=headers)
        return response.json()

    async def get_text(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> str:
        response = await self._get_with_backoff(url, params=params, headers=headers)
        return response.text

    async def _get_with_backoff(self, url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> httpx.Response:
        for attempt in range(self.http_429_retries + 1):
            await asyncio.sleep(self.request_delay_seconds)
            try:
                async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                    response = await client.get(url, params=params, headers=headers)
                    response.raise_for_status()
                    return response
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code != 429 or attempt >= self.http_429_retries:
                    raise
                await asyncio.sleep(self._retry_delay(exc.response, attempt))
        raise SourceError("Request failed after retrying rate-limited responses.")

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        retry_after = response.headers.get("retry-after")
        if retry_after and retry_after.isdigit():
            return min(float(retry_after), 60.0)
        return min(2.0 * (attempt + 1), 10.0)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " ".join(clean_text(item) for item in value)
    text = unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def abstract_from_inverted_index(index: dict[str, list[int]] | None) -> str:
    if not index:
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        for position in positions:
            words.append((position, word))
    return " ".join(word for _, word in sorted(words))


def first(value: Any) -> str:
    if isinstance(value, list) and value:
        return clean_text(value[0])
    return clean_text(value)


def unique(values: list[str]) -> list[str]:
    return [value for value in dict.fromkeys(clean_text(value) for value in values) if value]


def year_from_date(value: Any) -> int | None:
    text = clean_text(value)
    match = re.search(r"(19|20)\d{2}", text)
    return int(match.group(0)) if match else None
