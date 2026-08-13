"""Deterministic, explainable cost analytics."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from statistics import mean
from typing import Iterable
from .domain import CostRecord


def monthly_totals(records: Iterable[CostRecord]) -> dict[str, float]:
    totals: dict[str, Decimal] = defaultdict(Decimal)
    for record in records:
        totals[record.billing_period_start.isoformat()] += record.billed_cost
    return {period: float(amount.quantize(Decimal("0.01"))) for period, amount in sorted(totals.items())}


def summary(records: list[CostRecord], unit_volume: Decimal = Decimal("10000")) -> dict:
    by_provider: dict[str, Decimal] = defaultdict(Decimal)
    by_service: dict[str, Decimal] = defaultdict(Decimal)
    for record in records:
        by_provider[record.provider_name] += record.billed_cost
        by_service[record.service_name] += record.billed_cost
    monthly = monthly_totals(records)
    values = list(monthly.values())
    forecast = values[-1] if values else 0.0
    if len(values) > 1:
        forecast = max(0.0, values[-1] + values[-1] - values[-2])
    avg = mean(values) if values else 0.0
    anomalies = [{"period": period, "amount": amount, "reason": "above 1.25x mean", "threshold": round(avg * 1.25, 2)} for period, amount in monthly.items() if amount > avg * 1.25]
    total = sum((r.billed_cost for r in records), Decimal(0))
    volume = unit_volume if unit_volume > 0 else Decimal(1)
    prior = values[-2] if len(values) > 1 else None
    actual = values[-1] if values else 0.0
    return {"currency": "USD", "total": float(total.quantize(Decimal("0.01"))), "by_provider": {k: float(v) for k, v in sorted(by_provider.items())}, "by_service": {k: float(v) for k, v in sorted(by_service.items())}, "monthly": monthly, "forecast_next_month": round(forecast, 2), "variance": {"actual": actual, "prior": prior, "delta": round(actual - prior, 2) if prior is not None else None, "delta_pct": round((actual - prior) / prior * 100, 2) if prior else None}, "anomalies": anomalies, "unit_economics": {"orders": int(unit_volume), "cost_per_order": float((total / volume).quantize(Decimal("0.0001")))}}


def allocations(records: list[CostRecord], rules: list[dict]) -> dict:
    total_percent = sum(float(r["percent"]) for r in rules)
    if abs(total_percent - 100) > 1e-6:
        raise ValueError("allocation percentages must total 100")
    total = float(sum((r.billed_cost for r in records), Decimal(0)))
    return {"total": total, "allocations": [{"key": r["key"], "percent": float(r["percent"]), "amount": round(total * float(r["percent"]) / 100, 2)} for r in rules]}


def variance(records: list[CostRecord]) -> dict:
    series = monthly_totals(records)
    if len(series) < 2:
        return {"period": next(iter(series), None), "actual": next(iter(series.values()), 0.0), "prior": None, "delta": None, "delta_pct": None, "method": "month-over-month"}
    periods = list(series)
    actual, prior = series[periods[-1]], series[periods[-2]]
    return {"period": periods[-1], "actual": actual, "prior": prior, "delta": round(actual - prior, 2), "delta_pct": round((actual - prior) / prior * 100, 2) if prior else None, "method": "month-over-month"}
