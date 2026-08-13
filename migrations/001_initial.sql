CREATE TABLE IF NOT EXISTS import_runs (
  id UUID PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('queued','processing','completed','failed','dead_letter')),
  records_received INTEGER NOT NULL DEFAULT 0,
  records_inserted INTEGER NOT NULL DEFAULT 0,
  updated_count INTEGER NOT NULL DEFAULT 0,
  duplicate_count INTEGER NOT NULL DEFAULT 0,
  attempt INTEGER NOT NULL DEFAULT 0,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  completed_at TIMESTAMPTZ
);
ALTER TABLE import_runs ADD COLUMN IF NOT EXISTS updated_count INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS cost_records (
  id BIGSERIAL PRIMARY KEY,
  billing_period_start DATE NOT NULL,
  billing_period_end DATE NOT NULL,
  provider_name TEXT NOT NULL,
  service_name TEXT NOT NULL,
  billed_cost NUMERIC(18,6) NOT NULL CHECK (billed_cost >= 0),
  currency CHAR(3) NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  account_name TEXT,
  workload TEXT,
  tags JSONB NOT NULL DEFAULT '{}'::jsonb,
  consumed_quantity NUMERIC(18,6) CHECK (consumed_quantity >= 0),
  consumed_unit TEXT,
  source_hash TEXT NOT NULL,
  record_key TEXT NOT NULL UNIQUE,
  import_run_id UUID REFERENCES import_runs(id),
  imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE (source_hash)
);
CREATE INDEX IF NOT EXISTS cost_records_period_idx ON cost_records (billing_period_start, provider_name);
CREATE INDEX IF NOT EXISTS cost_records_workload_idx ON cost_records (workload);

CREATE TABLE IF NOT EXISTS allocation_rules (
  id BIGSERIAL PRIMARY KEY,
  rule_key TEXT NOT NULL UNIQUE,
  percent NUMERIC(7,4) NOT NULL CHECK (percent >= 0 AND percent <= 100),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS computed_reports (
  id BIGSERIAL PRIMARY KEY,
  report_type TEXT NOT NULL,
  period_start DATE,
  period_end DATE,
  payload JSONB NOT NULL,
  computed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS unit_metrics (
  id BIGSERIAL PRIMARY KEY,
  metric_key TEXT NOT NULL,
  period_start DATE NOT NULL,
  volume NUMERIC(18,6) NOT NULL CHECK (volume >= 0),
  unit TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'declared',
  UNIQUE(metric_key, period_start)
);
