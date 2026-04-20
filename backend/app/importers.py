from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from .models import PaperRecord


def _record_from_mapping(row: dict[str, object], source_name: str) -> PaperRecord:
    lower = {str(key).strip().lower(): value for key, value in row.items()}
    title = lower.get("title") or lower.get("ti") or lower.get("article title") or ""
    abstract = lower.get("abstract") or lower.get("ab") or lower.get("description") or ""
    doi = lower.get("doi") or lower.get("di") or ""
    journal = lower.get("journal") or lower.get("source title") or lower.get("jo") or ""
    year = lower.get("year") or lower.get("py") or lower.get("publication year") or None
    try:
        year_value = int(float(str(year))) if year else None
    except ValueError:
        year_value = None
    keywords = lower.get("keywords") or lower.get("author keywords") or lower.get("kw") or ""
    authors = lower.get("authors") or lower.get("author") or lower.get("au") or ""
    return PaperRecord(
        title=str(title or ""),
        abstract=str(abstract or ""),
        doi=str(doi or ""),
        journal=str(journal or ""),
        year=year_value,
        author_keywords=[item.strip() for item in str(keywords or "").split(";") if item.strip()],
        authors=[item.strip() for item in str(authors or "").replace(" and ", ";").split(";") if item.strip()],
        source_databases=[source_name],
        raw_record={str(key): value for key, value in row.items()},
    ).finalize_flags()


def import_records(path: Path, source_name: str = "import") -> list[PaperRecord]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return [_record_from_mapping(row, source_name) for row in csv.DictReader(handle)]
    if suffix in {".xlsx", ".xls"}:
        frame = pd.read_excel(path)
        return [_record_from_mapping(row, source_name) for row in frame.to_dict(orient="records")]
    if suffix == ".bib":
        return _import_bibtex(path, source_name)
    if suffix == ".ris":
        return _import_ris(path, source_name)
    raise ValueError(f"Unsupported import format: {suffix}")


def _import_ris(path: Path, source_name: str) -> list[PaperRecord]:
    records: list[PaperRecord] = []
    current: dict[str, list[str]] = {}
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if len(line) < 6 or "  - " not in line:
            continue
        tag, value = line[:2], line[6:].strip()
        if tag == "ER":
            records.append(
                _record_from_mapping(
                    {
                        "title": " ".join(current.get("TI", [])),
                        "abstract": " ".join(current.get("AB", [])),
                        "authors": "; ".join(current.get("AU", [])),
                        "year": current.get("PY", [""])[0],
                        "journal": " ".join(current.get("JO", [])),
                        "doi": current.get("DO", [""])[0],
                        "keywords": "; ".join(current.get("KW", [])),
                    },
                    source_name,
                )
            )
            current = {}
        else:
            current.setdefault(tag, []).append(value)
    return records


def _import_bibtex(path: Path, source_name: str) -> list[PaperRecord]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    records: list[PaperRecord] = []
    for chunk in text.split("@")[1:]:
        fields: dict[str, str] = {}
        for line in chunk.splitlines():
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            fields[key.strip().lower()] = value.strip().strip(",").strip("{}")
        if fields:
            records.append(_record_from_mapping(fields, source_name))
    return records

