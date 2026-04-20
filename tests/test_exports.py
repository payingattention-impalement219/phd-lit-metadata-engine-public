from pathlib import Path

from app import exports
from app.models import PaperRecord


def test_export_csv_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(exports, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(exports, "record_export", lambda *args, **kwargs: None)
    records = [PaperRecord(title="Export Me", abstract="Short abstract", doi="10.1/demo", source_databases=["test"])]

    result = exports.export_records("job-1", records, "csv")

    assert Path(result.path).exists()
    assert result.record_count == 1
    assert "Export Me" in Path(result.path).read_text(encoding="utf-8")


def test_export_ris_contains_title(tmp_path, monkeypatch):
    monkeypatch.setattr(exports, "REPORTS_DIR", tmp_path)
    monkeypatch.setattr(exports, "record_export", lambda *args, **kwargs: None)
    records = [PaperRecord(title="RIS Record", year=2024, source_databases=["test"])]

    result = exports.export_records("job-1", records, "ris")

    assert "TI  - RIS Record" in Path(result.path).read_text(encoding="utf-8")

