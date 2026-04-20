from app.dedupe import dedupe_records, normalize_doi
from app.models import PaperRecord


def test_normalize_doi_strips_url_prefix():
    assert normalize_doi("https://doi.org/10.1000/ABC") == "10.1000/abc"


def test_dedupe_merges_same_doi_sources():
    records = [
        PaperRecord(title="A Test Paper", doi="10.1000/demo", source_databases=["crossref"]),
        PaperRecord(title="A Test Paper", doi="https://doi.org/10.1000/demo", abstract="Abstract", source_databases=["openalex"]),
    ]

    deduped = dedupe_records(records)

    assert len(deduped) == 1
    assert deduped[0].abstract == "Abstract"
    assert set(deduped[0].source_databases) == {"crossref", "openalex"}


def test_dedupe_uses_fuzzy_title_year_when_identifiers_missing():
    records = [
        PaperRecord(title="Metadata Harvesting for PhD Literature Reviews", year=2025, source_databases=["a"]),
        PaperRecord(title="Metadata harvesting for PhD literature review", year=2025, source_databases=["b"]),
    ]

    deduped = dedupe_records(records)

    assert len(deduped) == 1
    assert set(deduped[0].source_databases) == {"a", "b"}

