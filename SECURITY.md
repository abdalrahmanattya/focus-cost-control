# Security

Report vulnerabilities privately to the repository owner. Never submit provider credentials, connection strings, customer billing data, or Terraform state. CSV imports are untrusted input; production deployments must add size limits, malware scanning, tenant authorization, managed identity, Key Vault private endpoint/DNS, private networking, and audit retention before accepting external files. Terraform state must use protected encrypted/versioned storage with audited least-privilege access before deployment.
