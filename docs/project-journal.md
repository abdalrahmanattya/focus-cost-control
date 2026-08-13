# Project journal

## 2026-08-13 — cloud-ready product path and architecture review

Implemented the bounded remediation in place. The repository now has a local
Compose product path (PostgreSQL, migration job, API, worker, dashboard), a
same-origin web proxy for the cloud path, MSAL Entra sign-in with local
auth-disabled mode, operator-group enforcement in the API, private Azure
PostgreSQL networking, managed-identity service bindings, and a one-shot cloud
migration Job before smoke. The dashboard covers sample CSV upload and status
polling, allocation rules, unit metrics, forecast/variance/anomalies, unit
economics, import retry/DLQ visibility, and CSV export.

Added editable landscape system/cloud SVGs with unchanged official Microsoft
Azure Architecture Icons and attribution. The cloud diagram is explicitly
labelled “CLOUD DEPLOYMENT NOT EXECUTED.” README, threat model, evidence
matrix, ADR, and Azure runbook now describe the same web/API/auth/network
boundary without claiming a deployment.

The final acceptance correction keeps the Container Apps environment
VNet-integrated but public at the platform edge (`internal_load_balancer_enabled
= false`); only the API ingress is internal. Storage and Service Bus now have
dedicated private endpoints, a private-endpoint subnet, public network access
disabled, and linked private DNS zones. The dashboard runtime uses the
unprivileged nginx image on port 8080, with an explicit local HTTP proxy and
cloud HTTPS proxy. Playwright now exercises the browser flow against clean
Compose, including upload/status, allocation and metric edits, analytics,
export, and import-state visibility.

### Verification evidence

- Python unit/API/auth/repository/deployment-contract tests: `13 passed, 1 warning`.
- Web dependency install, type check, Vite production build, and contract test:
  `npm ci`, `npm run check`, `npm run build`, and `npm test` passed (Vite emits
  the expected runtime `/config.js` non-module notice).
- Clean Compose E2E/restart/DLQ drill plus browser flow: `scripts/e2e.sh`
  passed (`5 passed`; Playwright `1 passed`) and its trap removed the Compose
  containers and volume.
- Terraform: fresh `fmt`, `init -backend=false`, and `validate` passed; no Azure
  apply occurred.
- SVG XML parsing passed for diagrams and official icon assets; Quick Look
  rendered refreshed PNG thumbnails for both diagrams and they were visually
  inspected. Render output remains outside the repository.
- Final standalone export check: the cloud SVG contains 9 embedded icon data
  URIs, zero relative asset references, and every decoded URI is byte-equal to
  its preserved official source SVG. `sips -s format png` produced complete
  1600x900 and 1600x1000 canvases; full-canvas inspection found no missing
  icons, red-X placeholders, black alpha backgrounds, clipping, or illegible
  diagram text.

### Resume point

The repository was published as the public
[`abdalrahmanattya/focus-cost-control`](https://github.com/abdalrahmanattya/focus-cost-control)
repository on `main`. Hosted CI run `31727920045` passed all five jobs,
including the API and dashboard non-root image builds, HIGH/CRITICAL Trivy
image gates, filesystem scan, and SBOM uploads. The final publication commits
are present locally and on `origin/main`; no release was created.

Cloud execution remains intentionally unperformed: no Azure apply, migration
Job run, cloud smoke, destroy, credentials, or deployment occurred. Re-run
local verification after review edits and obtain separate operator
authorization before any cloud action.
