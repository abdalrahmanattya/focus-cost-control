"""Storage adapters. Memory is the deterministic local default; PostgreSQL is production-ready."""
from __future__ import annotations
import json
import os
import threading
from datetime import datetime, timezone
from typing import Iterable
from .domain import CostRecord, ImportRun


class Repository:
    def records(self) -> list[CostRecord]: raise NotImplementedError
    def save_import(self, run: ImportRun, records: Iterable[CostRecord]) -> tuple[int, int]: raise NotImplementedError
    def get_import(self, run_id: str) -> ImportRun | None: raise NotImplementedError
    def list_imports(self) -> list[ImportRun]: raise NotImplementedError
    def register_import(self, run: ImportRun) -> None: raise NotImplementedError
    def update_import(self, run_id: str, status: str, *, attempt: int | None = None, error: str | None = None) -> None: raise NotImplementedError
    def save_unit_metric(self, metric: dict) -> None: raise NotImplementedError
    def unit_metrics(self) -> list[dict]: raise NotImplementedError
    def save_report(self, report_type: str, payload: dict) -> None: raise NotImplementedError
    def reports(self) -> list[dict]: raise NotImplementedError
    def save_rules(self, rules: list[dict]) -> None: raise NotImplementedError
    def rules(self) -> list[dict]: raise NotImplementedError


class MemoryRepository(Repository):
    def __init__(self, seed: Iterable[dict] = ()):
        self._records: dict[str, CostRecord] = {}
        self._runs: dict[str, ImportRun] = {}
        self._rules: list[dict] = []
        self._metrics: dict[tuple[str, str], dict] = {}
        self._reports: list[dict] = []
        self._lock = threading.RLock()
        for row in seed:
            from .domain import parse_record
            record = row if isinstance(row, CostRecord) else parse_record(row)
            self._records[record.record_key] = record
    def records(self):
        with self._lock: return sorted(self._records.values(), key=lambda r: (r.billing_period_start, r.provider_name, r.service_name))
    def save_import(self, run, records):
        inserted = updated = duplicates = 0
        with self._lock:
            for record in records:
                if record.record_key in self._records and self._records[record.record_key].source_hash == record.source_hash:
                    duplicates += 1
                else:
                    if record.record_key in self._records: updated += 1
                    else: inserted += 1
                    self._records[record.record_key] = record
            run.records_inserted, run.records_updated, run.duplicate_count = inserted, updated, duplicates
            run.status, run.completed_at = "completed", datetime.now(timezone.utc)
            self._runs[run.id] = run
        return inserted, duplicates
    def get_import(self, run_id): return self._runs.get(run_id)
    def list_imports(self): return list(self._runs.values())
    def register_import(self, run): self._runs[run.id] = run
    def update_import(self, run_id, status, *, attempt=None, error=None):
        run = self._runs.get(run_id)
        if run:
            run.status = status
            if attempt is not None: run.attempt = attempt
            run.error = error
    def save_rules(self, rules): self._rules = list(rules)
    def rules(self): return list(self._rules)
    def save_unit_metric(self, metric): self._metrics[(metric["metric_key"], metric["period_start"])] = dict(metric)
    def unit_metrics(self): return list(self._metrics.values())
    def save_report(self, report_type, payload): self._reports.append({"report_type": report_type, "payload": payload})
    def reports(self): return list(reversed(self._reports))


class PostgresRepository(Repository):
    def __init__(self, url: str): self.url = url
    def _connect(self):
        import psycopg
        return psycopg.connect(self.url)
    @staticmethod
    def _record(row):
        from .domain import CostRecord
        return CostRecord(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], row[8] or {}, row[9], row[10], row[11], row[12])
    def records(self):
        with self._connect() as c:
            rows = c.execute("SELECT billing_period_start,billing_period_end,provider_name,service_name,billed_cost,currency,account_name,workload,tags,consumed_quantity,consumed_unit,source_hash,record_key FROM cost_records ORDER BY billing_period_start,provider_name,service_name").fetchall()
        return [self._record(row) for row in rows]
    def save_import(self, run, records):
        inserted = duplicates = 0
        with self._connect() as c:
            c.execute("INSERT INTO import_runs (id,status,records_received,attempt) VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status,records_received=EXCLUDED.records_received,attempt=EXCLUDED.attempt", (run.id, "processing", run.records_received, run.attempt))
            updated = 0
            for r in records:
                cur = c.execute("""INSERT INTO cost_records (billing_period_start,billing_period_end,provider_name,service_name,billed_cost,currency,account_name,workload,tags,consumed_quantity,consumed_unit,source_hash,record_key,import_run_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s) ON CONFLICT (record_key) DO UPDATE SET billing_period_end=EXCLUDED.billing_period_end,billed_cost=EXCLUDED.billed_cost,currency=EXCLUDED.currency,tags=EXCLUDED.tags,consumed_quantity=EXCLUDED.consumed_quantity,consumed_unit=EXCLUDED.consumed_unit,source_hash=EXCLUDED.source_hash,import_run_id=EXCLUDED.import_run_id WHERE cost_records.source_hash <> EXCLUDED.source_hash RETURNING (xmax = 0) AS inserted""", (r.billing_period_start,r.billing_period_end,r.provider_name,r.service_name,r.billed_cost,r.currency,r.account,r.workload,json.dumps(r.tags or {}),r.consumed_quantity,r.consumed_unit,r.source_hash,r.record_key,run.id))
                result = cur.fetchone()
                if result and result[0]: inserted += 1
                elif result: updated += 1
                else: duplicates += 1
            run.records_inserted, run.records_updated, run.duplicate_count, run.status, run.completed_at = inserted, updated, duplicates, "completed", datetime.now(timezone.utc)
            c.execute("UPDATE import_runs SET status=%s,records_inserted=%s,updated_count=%s,duplicate_count=%s,completed_at=%s,error=%s WHERE id=%s", (run.status, inserted, updated, duplicates, run.completed_at, run.error, run.id))
        return inserted, updated, duplicates
    def get_import(self, run_id):
        with self._connect() as c:
            row = c.execute("SELECT id,status,records_received,records_inserted,updated_count,duplicate_count,attempt,error,created_at,completed_at FROM import_runs WHERE id=%s", (run_id,)).fetchone()
        if not row: return None
        return ImportRun(*row)
    def list_imports(self):
        with self._connect() as c:
            rows = c.execute("SELECT id,status,records_received,records_inserted,updated_count,duplicate_count,attempt,error,created_at,completed_at FROM import_runs ORDER BY created_at DESC").fetchall()
        return [ImportRun(*row) for row in rows]
    def update_import(self, run_id, status, *, attempt=None, error=None):
        with self._connect() as c:
            c.execute("UPDATE import_runs SET status=%s,attempt=COALESCE(%s,attempt),error=%s WHERE id=%s", (status, attempt, error, run_id))
    def register_import(self, run):
        with self._connect() as c:
            c.execute("INSERT INTO import_runs (id,status,records_received,attempt) VALUES (%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING", (run.id, run.status, run.records_received, run.attempt))
    def save_rules(self, rules):
        with self._connect() as c:
            c.execute("DELETE FROM allocation_rules")
            for r in rules: c.execute("INSERT INTO allocation_rules(rule_key,percent) VALUES (%s,%s)", (r["key"], r["percent"]))
    def rules(self):
        with self._connect() as c: rows = c.execute("SELECT rule_key,percent FROM allocation_rules ORDER BY rule_key").fetchall()
        return [{"key": row[0], "percent": float(row[1])} for row in rows]
    def save_unit_metric(self, metric):
        with self._connect() as c:
            c.execute("INSERT INTO unit_metrics(metric_key,period_start,volume,unit,source) VALUES (%s,%s,%s,%s,%s) ON CONFLICT (metric_key,period_start) DO UPDATE SET volume=EXCLUDED.volume,unit=EXCLUDED.unit,source=EXCLUDED.source", (metric["metric_key"], metric["period_start"], metric["volume"], metric["unit"], metric.get("source", "declared")))
    def unit_metrics(self):
        with self._connect() as c: rows = c.execute("SELECT metric_key,period_start,volume,unit,source FROM unit_metrics ORDER BY period_start DESC").fetchall()
        return [{"metric_key": r[0], "period_start": str(r[1]), "volume": float(r[2]), "unit": r[3], "source": r[4]} for r in rows]
    def save_report(self, report_type, payload):
        with self._connect() as c: c.execute("INSERT INTO computed_reports(report_type,payload) VALUES (%s,%s::jsonb)", (report_type, json.dumps(payload)))
    def reports(self):
        with self._connect() as c: rows = c.execute("SELECT report_type,payload,computed_at FROM computed_reports ORDER BY computed_at DESC LIMIT 50").fetchall()
        return [{"report_type": r[0], "payload": r[1], "computed_at": r[2].isoformat()} for r in rows]


def get_repository(seed: Iterable[dict] = ()) -> Repository:
    return PostgresRepository(os.environ["DATABASE_URL"]) if os.getenv("DATABASE_URL") else MemoryRepository(seed)
