# Azure ephemeral runbook

This runbook describes a planned, unexecuted workflow. Owners are the release
operator (execution/evidence), platform owner (Azure/network/state), budget
owner (cost approval), and security owner (identity/retention/recovery review).

## Prerequisites and protected inputs

Use a protected GitHub environment with OIDC and least-privilege Azure role
assignments. Protect `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`,
`AZURE_SUBSCRIPTION_ID`, `POSTGRES_ADMIN_PASSWORD` (at least 16 characters),
immutable `CONTAINER_IMAGE` and `WEB_IMAGE` digests, `ENTRA_TENANT_ID`,
`ENTRA_SPA_CLIENT_ID`, `ENTRA_API_CLIENT_ID`, `ENTRA_OPERATOR_GROUP_ID`, and
the remote state coordinates `TF_STATE_RESOURCE_GROUP`,
`TF_STATE_STORAGE_ACCOUNT`, `TF_STATE_CONTAINER`, and `TF_STATE_KEY`. Do not
place credentials, connection strings, or state files in the repository.

The platform owner must confirm encrypted/versioned remote state, access logs,
least-privilege state access, retention, restore testing, budgets/alerts/tags,
and the Key Vault private endpoint/DNS blocker before approval. The budget
owner records the current Azure Pricing Calculator estimate against the
pre-approved threshold. The release operator records plan IDs, approvals,
workflow logs, outputs, smoke results, and destroy confirmation.

## PLAN gate

Run the protected plan workflow with `PLAN-ONLY` and the exact image/state
inputs. The workflow sets `TF_VAR_enable_apply=true` to evaluate the real
graph while making no mutation. Review the resource counts, SKUs, network exposure,
secret/state behavior, and estimated cost. Exit criteria: plan is reviewed by
platform, security, and budget owners; no unresolved Key Vault public-path
hardening gap and verified RBAC/authentication boundary;
and the evidence bundle contains the plan and approvals. Roll back by stopping
before APPLY; no cloud mutation occurs in PLAN.

## APPLY and MIGRATION gates

Use the protected `azure-apply` environment and `APPLY-APPROVED` confirmation.
APPLY runs Terraform with `enable_apply=true` using immutable image digests.
Record Terraform outputs, resource identifiers, and the derived web URL. Then
run the one-shot migration Job and record completion before smoke. If apply or
migration fails, stop, retain logs, and use the reviewed Terraform rollback or
DESTROY decision; do not improvise changes in the cloud.

## SMOKE gate

The smoke operator uses the output-derived web URL, authenticates through
Entra, imports only the synthetic fixture, verifies status, dedupe, analytics,
allocation, and unit economics, and stores sanitized evidence. Export is
covered by the local browser tests, not this cloud smoke gate. Exit
criteria are successful checks, no credential leakage, and recorded timestamps.
Failure blocks acceptance and triggers the rollback decision.

## DESTROY gate and data-loss warning

At the end of the default acceptance window (at most two hours), the release
operator escalates to the named owner if the resources are still running. Run
`azure-destroy` only with a separate protected confirmation, then verify the
resource group is absent and retain the destroy evidence. `force_destroy` or
equivalent deletion of storage can permanently delete imported data; it is a
data-loss operation and must never be enabled for shared or production data.

## Recovery requirements

Required targets, not evidence: raw imports retained 30 days, normalized
cost/report records 90 days, audit/telemetry 30 days, RPO at most 24 hours,
and RTO at most 4 hours. Perform a restore drill before first deployment and
quarterly thereafter, with the security/platform owners recording the result.
