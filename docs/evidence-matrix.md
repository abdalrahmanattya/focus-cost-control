# Evidence matrix

| Capability | Local evidence | Boundary |
|---|---|---|
| FOCUS import | `src/focus_cost/importer.py`, `tests/test_api.py` | FOCUS 1.4 practical subset |
| Cost intelligence | `src/focus_cost/analytics.py`, API tests | Deterministic heuristics; no financial advice |
| Async processing | `src/focus_cost/jobs.py`, import status tests | Azure adapter requires managed identity |
| PostgreSQL | `migrations/001_initial.sql`, Compose migration + persistence drill | Azure uses a delegated private subnet and private DNS; no cloud apply here |
| Dashboard | `web`, npm check/build/test, `scripts/e2e.sh` | Browser flow covers upload, polling, analytics, editing, export; no hosted browser run here |
| Cloud web/auth | `infra/azure`, `web/nginx.conf.template`, `web/src/auth.ts` | Public web only; internal API validates Entra JWT and operator group |
| Azure delivery | `infra/azure`, protected OIDC workflows, runbook | Plan/apply/smoke/destroy are structurally complete; no apply or cloud smoke was executed here |
| Architecture | `docs/diagrams/*.svg`, official icon assets | SVGs are editable review artifacts; cloud diagram is explicitly unexecuted |
