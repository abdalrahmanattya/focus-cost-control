# Cost model

Costs are stored as non-negative decimal amounts with ISO currency and billing period. Forecast is the latest-period delta extrapolation, anomalies are periods above 1.25 times the mean, and unit economics divide total cost by the declared workload volume. These deterministic heuristics are explainable operational signals, not financial advice.

The bounded Azure resource envelope covers the planned Container Apps
environment, web/API apps, worker and migration Jobs, PostgreSQL, Service Bus,
Blob Storage, Key Vault, VNet/private endpoints/private DNS, and Application
Insights/logging. It is a pre-deployment gate, not a live estimate:
the platform owner records exact Terraform SKUs and resource counts, the
budget owner records the current Azure Pricing Calculator estimate against the
pre-approved threshold, and the release operator retains the approval and
destroy evidence. The default acceptance window is at most two hours with a
named owner and escalation contact; a missed window triggers DESTROY review.
