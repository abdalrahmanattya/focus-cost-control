# Requirements and acceptance criteria

- Import a UTF-8 CSV subset with the six required FOCUS 1.4 fields; reject malformed, oversized, negative, or unsupported records with field-level errors.
- Persist import runs, cost records, allocation rules, unit metrics, and computed report history in PostgreSQL. A natural record key permits late corrections; an unchanged source hash is idempotent. Unit metric inputs drive unit economics.
- Return 202 for imports and expose queued, processing, completed, failed, and dead-letter states. Local jobs retry three times; Azure jobs use Service Bus delivery count and its dead-letter subqueue.
- Keep forecast, variance, anomaly, allocation, and unit-economics calculations deterministic and explainable.
- Provide a responsive accessible dashboard with import status, costs, provider allocation, forecasts, anomalies, unit economics, upload, refresh, and CSV export.
- Cloud deployment must use managed identities, RBAC, Key Vault references, network-private Blob and Service Bus endpoints with private DNS, private PostgreSQL, App Insights, health probes, and a queue-triggered worker. The public web edge uses MSAL with a separate SPA client ID; the internal API validates the Entra API audience and operator group.
