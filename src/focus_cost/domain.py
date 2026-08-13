"""Domain types and validation primitives for Focus Cost Control."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any

REQUIRED_COLUMNS = {
    "BillingPeriodStart", "BillingPeriodEnd", "ProviderName", "ServiceName",
    "BilledCost", "Currency",
}
OPTIONAL_COLUMNS = {"Account", "Workload", "Tags", "ConsumedQuantity", "ConsumedUnit"}


class ValidationError(ValueError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


@dataclass(frozen=True)
class CostRecord:
    billing_period_start: date
    billing_period_end: date
    provider_name: str
    service_name: str
    billed_cost: Decimal
    currency: str
    account: str | None = None
    workload: str | None = None
    tags: dict[str, str] | None = None
    consumed_quantity: Decimal | None = None
    consumed_unit: str | None = None
    source_hash: str = ""
    record_key: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "BillingPeriodStart": self.billing_period_start.isoformat(),
            "BillingPeriodEnd": self.billing_period_end.isoformat(),
            "ProviderName": self.provider_name,
            "ServiceName": self.service_name,
            "BilledCost": float(self.billed_cost),
            "Currency": self.currency,
            "Account": self.account,
            "Workload": self.workload,
            "Tags": self.tags or {},
            "ConsumedQuantity": float(self.consumed_quantity) if self.consumed_quantity is not None else None,
            "ConsumedUnit": self.consumed_unit,
            "SourceHash": self.source_hash,
            "RecordKey": self.record_key,
        }


def _decimal(value: Any, field: str) -> Decimal:
    try:
        number = Decimal(str(value).strip())
    except (InvalidOperation, ValueError, AttributeError):
        raise ValidationError(f"{field} must be numeric", {"field": field}) from None
    if not number.is_finite() or number < 0:
        raise ValidationError(f"{field} must be non-negative", {"field": field})
    return number.quantize(Decimal("0.000001"))


def parse_record(row: dict[str, Any]) -> CostRecord:
    missing = sorted(REQUIRED_COLUMNS - set(row))
    if missing:
        raise ValidationError("required columns are missing", {"missing_columns": missing})
    values = {key: str(row.get(key, "")).strip() for key in REQUIRED_COLUMNS}
    values.update({key: str(row.get(key, "")).strip() for key in OPTIONAL_COLUMNS if key in row})
    if any(not values[key] for key in REQUIRED_COLUMNS):
        raise ValidationError("required fields cannot be blank")
    try:
        start = date.fromisoformat(values["BillingPeriodStart"])
        end = date.fromisoformat(values["BillingPeriodEnd"])
    except ValueError:
        raise ValidationError("billing periods must be ISO dates") from None
    if end < start:
        raise ValidationError("BillingPeriodEnd must not precede BillingPeriodStart")
    currency = values["Currency"].upper()
    if len(currency) != 3 or not currency.isalpha():
        raise ValidationError("Currency must be an ISO 4217 code")
    if currency != "USD":
        raise ValidationError("only USD is accepted; no implicit FX conversion is performed")
    tags: dict[str, str] = {}
    raw_tags = row.get("Tags")
    if raw_tags:
        try:
            tags = json.loads(raw_tags) if isinstance(raw_tags, str) else dict(raw_tags)
        except (ValueError, TypeError):
            raise ValidationError("Tags must be a JSON object") from None
        if not isinstance(tags, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in tags.items()):
            raise ValidationError("Tags must be a JSON object of strings")
    record_key = "|".join([values["BillingPeriodStart"], values["BillingPeriodEnd"], values["ProviderName"], values["ServiceName"], values.get("Account", ""), values.get("Workload", "")])
    canonical = json.dumps({k: row.get(k, "") for k in sorted(row)}, sort_keys=True, separators=(",", ":"), default=str)
    return CostRecord(
        start, end, values["ProviderName"], values["ServiceName"], _decimal(values["BilledCost"], "BilledCost"), currency,
        values.get("Account") or None, values.get("Workload") or None, tags,
        _decimal(row["ConsumedQuantity"], "ConsumedQuantity") if row.get("ConsumedQuantity") not in (None, "") else None,
        str(row.get("ConsumedUnit", "")).strip() or None,
        hashlib.sha256(canonical.encode()).hexdigest(), record_key,
    )


@dataclass
class ImportRun:
    id: str
    status: str
    records_received: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    duplicate_count: int = 0
    attempt: int = 0
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    def as_dict(self) -> dict[str, Any]:
        return {"id": self.id, "status": self.status, "records_received": self.records_received, "records_inserted": self.records_inserted, "records_updated": self.records_updated, "duplicate_count": self.duplicate_count, "attempt": self.attempt, "error": self.error, "created_at": self.created_at.isoformat(), "completed_at": self.completed_at.isoformat() if self.completed_at else None}
