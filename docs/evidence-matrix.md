# Evidence matrix

Evidence is dated and reproducible where local commands are available. Hosted
CI run **31732035428** is the authoritative pre-remediation hosted baseline;
31727920045 is superseded historical evidence. Neither is evidence for this
changed revision; the expanded revision awaits its PR run.

| Capability | Local evidence | Boundary |
|---|---|---|
| FOCUS import | `2026-08-16: PYTHONPATH=src .venv/bin/pytest -q` (13 passed) | FOCUS 1.4 practical subset |
| Cost intelligence | `src/focus_cost/analytics.py`, API tests | Deterministic heuristics; no financial advice |
| Async processing | `src/focus_cost/jobs.py`, import status tests | Azure adapter requires managed identity |
| PostgreSQL | `2026-08-16: docker compose config --quiet`; isolated `scripts/e2e.sh` lifecycle with restart persistence; `migrations/001_initial.sql` | Azure uses a delegated private subnet and private DNS; no cloud apply here |
| Dashboard | `2026-08-16: scripts/e2e.sh` Playwright flow (`1 passed`) plus headless Chrome capture of `docs/assets/local-ui.png` | Local auth-disabled synthetic evidence covers upload/status, allocation, unit metric, analytics, export, and DLQ; no hosted browser run here |
| Cloud web/auth | `infra/azure`, `web/nginx.conf.template`, `web/src/auth.ts` | Public web only; internal API validates Entra JWT and operator group |
| Azure delivery | `2026-08-16: terraform fmt -check -recursive`; hosted CI 31732035428 | Pre-remediation hosted baseline only; expanded revision awaits PR evidence; plan/apply/smoke/destroy remain unexecuted |
| Architecture | `docs/diagrams/*.svg`, official icon assets | SVGs are editable review artifacts; cloud diagram is explicitly unexecuted |
