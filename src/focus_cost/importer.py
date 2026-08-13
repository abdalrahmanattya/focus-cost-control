"""FOCUS-compatible CSV parsing and validation."""
from __future__ import annotations
import csv, io
from typing import Iterable
from .domain import CostRecord, REQUIRED_COLUMNS, ValidationError, parse_record

def parse_csv(raw: bytes) -> list[CostRecord]:
    if len(raw) > 10 * 1024 * 1024: raise ValidationError("CSV exceeds the 10 MiB limit")
    try: text = raw.decode("utf-8-sig")
    except UnicodeDecodeError: raise ValidationError("CSV must be UTF-8") from None
    reader = csv.DictReader(io.StringIO(text))
    fields = set(reader.fieldnames or [])
    missing = sorted(REQUIRED_COLUMNS - fields)
    if missing: raise ValidationError("FOCUS 1.4 compatible subset is missing required columns", {"missing_columns": missing, "format": "FOCUS 1.4 subset"})
    rows: list[CostRecord] = []
    for number, row in enumerate(reader, 2):
        try: rows.append(parse_record(row))
        except ValidationError as exc: raise ValidationError(f"row {number}: {exc}", exc.details) from None
    if not rows: raise ValidationError("CSV must contain at least one data row")
    return rows
