# API contract

All endpoints are under `/api/v1`. JSON errors use `detail.message`; validation errors may also include `missing_columns` and `field`.

| Method | Route | Purpose |
|---|---|---|
| GET | `/summary` | Total, provider/service totals, monthly totals, forecast, anomalies, unit economics |
| GET | `/costs` or `/records` | Imported normalized cost records |
| POST | `/imports` | Multipart CSV upload; returns 202 and `import_id` |
| GET | `/imports` or `/imports/{id}` | Queue depth and import run state |
| GET/POST | `/allocations` | Read or validate/persist rules totalling 100% |
| GET | `/forecasts` | Forecast and source monthly series |
| GET | `/variance` | Latest month-over-month actual, prior, delta, and percentage |
| GET | `/anomalies` | Periods above 1.25× mean |
| GET | `/unit-economics` | Cost per declared 10,000 orders |
| GET/POST | `/unit-metrics` | Persist/list declared volumes such as orders |
| GET | `/reports` | Persisted deterministic report snapshots |
