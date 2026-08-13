from datetime import date
from decimal import Decimal
import time

import pytest

from focus_cost.domain import ValidationError, parse_record
from focus_cost.importer import parse_csv
from focus_cost.repository import MemoryRepository
from focus_cost.jobs import ImportWorker
from focus_cost.domain import ImportRun

CSV = b"BillingPeriodStart,BillingPeriodEnd,ProviderName,ServiceName,BilledCost,Currency,Account,Workload\n2026-03-01,2026-03-31,AWS,Storage,10,USD,prod,files\n"

def test_parser_is_strict_and_supports_optional_dimensions():
    row = parse_csv(CSV)[0]
    assert row.billing_period_start == date(2026, 3, 1)
    assert row.billed_cost == Decimal("10.000000")
    assert row.record_key.endswith("prod|files")

@pytest.mark.parametrize("value", [b"", b"BillingPeriodStart,ProviderName\n2026-01-01,AWS\n"])
def test_parser_rejects_empty_or_missing_required(value):
    with pytest.raises(ValidationError): parse_csv(value)

def test_idempotency_and_late_correction():
    repo = MemoryRepository()
    worker = ImportWorker(repo)
    first = worker.enqueue(parse_csv(CSV))
    for _ in range(100):
        if repo.get_import(first.id) and repo.get_import(first.id).status == "completed": break
        time.sleep(0.001)
    duplicate = worker.enqueue(parse_csv(CSV))
    corrected = parse_csv(CSV.replace(b",10,USD,", b",12,USD,"))
    changed = worker.enqueue(corrected)
    for _ in range(100):
        if repo.get_import(changed.id) and repo.get_import(changed.id).status == "completed": break
        time.sleep(0.001)
    assert repo.get_import(duplicate.id) is not None
    assert repo.records()[0].billed_cost == Decimal("12.000000")
    assert repo.get_import(changed.id).records_updated == 1

class AlwaysFailRepository(MemoryRepository):
    def save_import(self, run, records): raise RuntimeError("synthetic storage outage")

def test_worker_persists_retry_and_dead_letter_state():
    repo = AlwaysFailRepository()
    worker = ImportWorker(repo, max_attempts=2)
    run = worker.enqueue(parse_csv(CSV))
    for _ in range(200):
        state = repo.get_import(run.id)
        if state and state.status == "dead_letter": break
        time.sleep(0.002)
    state = repo.get_import(run.id)
    assert state.status == "dead_letter"
    assert state.attempt == 2
    assert "synthetic storage outage" in state.error
