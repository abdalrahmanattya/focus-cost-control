# Focus Cost Control

## What it is

Focus Cost Control is a complete, runnable cost-intelligence service for a
validated subset of the [FOCUS 1.4](https://focus.finops.org/) billing format.
It turns AWS, Azure, and AI-provider CSV exports into explainable costs,
allocation rules, deterministic forecasts, anomaly signals, and unit
economics.

## Why it exists

Cloud cost data is often imported asynchronously but reviewed synchronously.
This project makes the boundary visible: every import has a durable status,
lineage, retry attempt, duplicate/late-correction count, and error or
dead-letter state. Analytics are deterministic and inspectable rather than
presented as financial advice.

## What it does

- Validates UTF-8 FOCUS CSV files (size, dates, currency, non-negative amounts,
  required columns) and deduplicates natural keys while applying late updates.
- Persists cost records, imports, allocation rules, unit metrics, and report
  snapshots in PostgreSQL; an in-memory adapter keeps fast tests and local
  development credential-free.
- Runs imports through an asynchronous worker with retry and dead-letter
  behavior. Compose includes API, dashboard, migration, worker, and Postgres.
- Exposes allocation validation, variance, forecast, anomaly, unit economics,
  import status, and CSV export through a versioned REST API.
- Provides an accessible responsive dashboard for CSV upload, status polling,
  allocation-rule editing, unit-metric input, analytics, and export.

## How it works

![Local system architecture](docs/diagrams/system-architecture.svg)

![Azure deployment architecture](docs/diagrams/cloud-architecture.svg)

The local system uses the same API and repository contracts with either an
in-memory queue or PostgreSQL-backed Compose services. In cloud mode, the web
Container App is the only public ingress: nginx proxies `/api` to an internal
API Container App, and the browser obtains an Entra bearer token with MSAL.
PostgreSQL is VNet-integrated with a delegated private subnet and private DNS;
Blob Storage and Service Bus have public network access disabled and use private
endpoints, private DNS, and identity-authorized access.
The cloud shape is documented but not applied; see the explicit banner in the
cloud diagram.

Official Microsoft Azure Architecture Icons are used unchanged in the cloud
diagram. Source and attribution are recorded in
[`docs/diagrams/README.md`](docs/diagrams/README.md).

## Run locally

### Python API and worker

```sh
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
PYTHONPATH=src .venv/bin/pytest -q
PYTHONPATH=src .venv/bin/uvicorn focus_cost.main:app --reload
```

The API listens on `http://127.0.0.1:8000`. Local auth is intentionally
disabled (`AUTH_REQUIRED=false`) and must not be used as a production boundary.

### Full Compose stack

```sh
docker compose up --build
```

Open `http://127.0.0.1:5173`. Compose runs migrations before the worker and
dashboard, and persists PostgreSQL data in the `postgres-data` volume. The
dashboard is configured for local auth-disabled mode. To validate the complete
workflow, run:

```sh
./scripts/e2e.sh
```

The script uploads the synthetic fixture, polls completion, asserts dedupe,
analytics, allocation, and unit economics, then checks restart persistence and
retry/dead-letter visibility. It removes only its own Compose containers and
volume on exit.

## Guided demo

1. Start Compose and open the dashboard.
2. Choose **Import CSV** and select
   [`fixtures/sample_focus.csv`](fixtures/sample_focus.csv).
3. Watch **Import status** move from queued to completed and inspect inserted,
   updated, and duplicate counts.
4. Edit the allocation rule and save an orders unit metric.
5. Review monthly trend, forecast, variance, anomalies, and cost-per-order.
6. Choose **Export costs** to download the normalized CSV.

The fixture is synthetic and contains no credentials or customer data.

## API

`GET /health`, `GET /api/v1/summary`, `GET /api/v1/costs`,
`GET /api/v1/records`, `GET/POST /api/v1/imports`,
`GET /api/v1/imports/{id}`, `GET/POST /api/v1/allocations`,
`GET /api/v1/forecasts`, `GET /api/v1/variance`, `GET /api/v1/anomalies`,
`GET /api/v1/unit-economics`, `GET/POST /api/v1/unit-metrics`, and
`GET /api/v1/reports` are documented in [`docs/api.md`](docs/api.md).

`POST /api/v1/imports` returns `202 Accepted` with an import ID and zero
records inserted while work is pending. Poll the import resource for the
durable result. Mutating routes require the operator group when cloud auth is
enabled.

## Tests and development

```sh
PYTHONPATH=src .venv/bin/pytest -q
cd web && npm ci && npm run check && npm run build && npm test
cd ..
terraform -chdir=infra/azure fmt -check -recursive
terraform -chdir=infra/azure init -backend=false
terraform -chdir=infra/azure validate
```

See [`docs/development.md`](docs/development.md),
[`docs/requirements.md`](docs/requirements.md), and
[`CONTRIBUTING.md`](CONTRIBUTING.md) for contracts, migrations, test seams, and
review expectations.

## Cloud deployment

`infra/azure` is a runnable Terraform module for the documented cloud shape:
public web Container App, internal API Container App, queue-triggered worker
and one-shot migration Jobs, private Blob/Service Bus, private PostgreSQL,
Key Vault, managed identities/RBAC, Application Insights, health probes, and
autoscaling. Protected OIDC workflows accept immutable image digests, durable
state inputs, typed confirmations, environment gates, and output-derived
smoke/destroy checks.

No cloud resources, credentials, deployment, smoke, or destroy were executed
for this local implementation. Applying requires an operator-owned GitHub
environment, non-placeholder secret inputs, and explicit cost approval. Follow
[`docs/runbooks/azure.md`](docs/runbooks/azure.md); run the migration Job before
the authenticated smoke test.

## Security and limitations

Cloud mode uses Microsoft Entra MSAL in the web app and validates JWT issuer,
audience, signature, and operator group in the API. The API is internal in the
Terraform graph, while nginx exposes only the authenticated same-origin web
path. Managed identity and Key Vault references keep database credentials out
of images and source. Read [`SECURITY.md`](SECURITY.md) and
[`docs/threat-model.md`](docs/threat-model.md) before deployment.

Forecasts, anomalies, allocation results, and unit economics are deterministic
operational heuristics, not financial, accounting, or security advice. FOCUS
support is a bounded subset, not a claim of full specification coverage. The
local auth-disabled mode, synthetic fixture, and unexecuted cloud diagram are
deliberate limitations.

MIT licensed.
