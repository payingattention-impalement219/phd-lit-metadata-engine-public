import httpx
import pytest

from app.models import SearchRequest, SourceName
from app.sources.registry import list_source_statuses
from app.sources.semantic_scholar import SEMANTIC_SCHOLAR_BULK_URL, SemanticScholarClient


@pytest.mark.asyncio
async def test_semantic_scholar_runs_without_api_key(monkeypatch):
    captured = {}

    async def fake_get_json(self, url, *, params=None, headers=None):
        captured["url"] = url
        captured["params"] = params
        captured["headers"] = headers
        return {"data": [{"title": "Open metadata", "externalIds": {}, "authors": []}]}

    monkeypatch.setattr("app.sources.semantic_scholar.settings.semantic_scholar_api_key", "")
    monkeypatch.setattr(SemanticScholarClient, "get_json", fake_get_json)

    records = await SemanticScholarClient().search(SearchRequest(query="concept A method term", sources=[SourceName.semantic_scholar]))

    assert records[0].title == "Open metadata"
    assert captured["url"] == SEMANTIC_SCHOLAR_BULK_URL
    assert captured["params"]["query"] == "concept A method term"
    assert captured["params"]["limit"] == 25
    assert "paperId" in captured["params"]["fields"]
    assert captured["headers"] == {}


@pytest.mark.asyncio
async def test_semantic_scholar_uses_optional_api_key(monkeypatch):
    captured = {}

    async def fake_get_json(self, url, *, params=None, headers=None):
        captured["headers"] = headers
        return {"data": []}

    monkeypatch.setattr("app.sources.semantic_scholar.settings.semantic_scholar_api_key", "demo-key")
    monkeypatch.setattr(SemanticScholarClient, "get_json", fake_get_json)

    await SemanticScholarClient().search(SearchRequest(query="concept A method term", sources=[SourceName.semantic_scholar]))

    assert captured["headers"] == {"x-api-key": "demo-key"}


@pytest.mark.asyncio
async def test_semantic_scholar_follows_bulk_pagination_token(monkeypatch):
    calls = []

    async def fake_get_json(self, url, *, params=None, headers=None):
        calls.append(dict(params or {}))
        if len(calls) == 1:
            return {
                "data": [
                    {
                        "paperId": "first",
                        "title": "First page",
                        "externalIds": {"DOI": "10.1/first", "PubMed": "123"},
                        "authors": [{"name": "A Author"}],
                        "fieldsOfStudy": ["Medicine"],
                        "isOpenAccess": True,
                    }
                ],
                "token": "next-page-token",
            }
        return {
            "data": [
                {
                    "paperId": "second",
                    "title": "Second page",
                    "externalIds": {"PubMedCentral": "PMC123"},
                    "authors": [{"name": "B Author"}],
                }
            ]
        }

    monkeypatch.setattr("app.sources.semantic_scholar.settings.semantic_scholar_api_key", "")
    monkeypatch.setattr(SemanticScholarClient, "get_json", fake_get_json)

    records = await SemanticScholarClient().search(
        SearchRequest(query="concept A method term", sources=[SourceName.semantic_scholar], max_results_per_source=2)
    )

    assert [record.title for record in records] == ["First page", "Second page"]
    assert records[0].doi == "10.1/first"
    assert records[0].pmid == "123"
    assert records[0].open_access_status == "open"
    assert records[1].pmcid == "PMC123"
    assert calls[0]["limit"] == 2
    assert "token" not in calls[0]
    assert calls[1]["token"] == "next-page-token"


@pytest.mark.asyncio
async def test_semantic_scholar_stops_at_requested_max(monkeypatch):
    async def fake_get_json(self, url, *, params=None, headers=None):
        return {
            "data": [
                {"paperId": "one", "title": "One", "externalIds": {}, "authors": []},
                {"paperId": "two", "title": "Two", "externalIds": {}, "authors": []},
            ],
            "token": "unused-next-page",
        }

    monkeypatch.setattr("app.sources.semantic_scholar.settings.semantic_scholar_api_key", "")
    monkeypatch.setattr(SemanticScholarClient, "get_json", fake_get_json)

    records = await SemanticScholarClient().search(
        SearchRequest(query="concept A method term", sources=[SourceName.semantic_scholar], max_results_per_source=1)
    )

    assert [record.title for record in records] == ["One"]


@pytest.mark.asyncio
async def test_semantic_scholar_retries_rate_limits(monkeypatch):
    attempts = {"count": 0}

    async def fake_get_json(self, url, *, params=None, headers=None):
        attempts["count"] += 1
        if attempts["count"] == 1:
            response = httpx.Response(429, request=httpx.Request("GET", url), headers={"retry-after": "0"})
            raise httpx.HTTPStatusError("rate limited", request=response.request, response=response)
        return {"data": []}

    monkeypatch.setattr("app.sources.semantic_scholar.settings.semantic_scholar_api_key", "")
    monkeypatch.setattr(SemanticScholarClient, "get_json", fake_get_json)

    async def no_sleep(delay):
        return None

    monkeypatch.setattr("app.sources.semantic_scholar.asyncio.sleep", no_sleep)

    await SemanticScholarClient().search(SearchRequest(query="concept A method term", sources=[SourceName.semantic_scholar]))

    assert attempts["count"] == 2


def test_semantic_scholar_source_status_is_free_and_available(monkeypatch):
    monkeypatch.setattr("app.sources.semantic_scholar.settings.semantic_scholar_api_key", "")

    statuses = {status.name: status for status in list_source_statuses()}
    semantic_scholar = statuses[SourceName.semantic_scholar]

    assert semantic_scholar.available is True
    assert semantic_scholar.requires_key is False
    assert semantic_scholar.configured is True
