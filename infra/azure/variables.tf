variable "location" {
  type    = string
  default = "westeurope"
}
variable "name" {
  type    = string
  default = "focuscostcontrol"
}
variable "enable_apply" {
  type        = bool
  default     = false
  description = "Explicit operator gate."
}
variable "container_image" {
  type        = string
  description = "Immutable API/worker image; required for apply."
  nullable    = false
}
variable "web_image" {
  type        = string
  description = "Immutable web image digest; required for apply."
  nullable    = false
}
variable "postgres_admin_password" {
  type        = string
  sensitive   = true
  description = "Protected deployment input."
  nullable    = false
  validation {
    condition     = length(var.postgres_admin_password) >= 16
    error_message = "postgres_admin_password must be at least 16 characters."
  }
}
variable "postgres_admin_login" {
  type    = string
  default = "focusadmin"
  validation {
    condition     = can(regex("^[a-z][a-z0-9_]{2,31}$", var.postgres_admin_login))
    error_message = "postgres_admin_login must be a valid PostgreSQL identifier."
  }
}
variable "entra_tenant_id" {
  type        = string
  description = "Microsoft Entra tenant used to validate bearer tokens."
  default     = ""
  validation {
    condition     = !var.enable_apply || length(var.entra_tenant_id) > 0
    error_message = "entra_tenant_id is required when enable_apply is true."
  }
}
variable "entra_spa_client_id" {
  type        = string
  description = "Microsoft Entra public SPA client ID used by MSAL."
  default     = ""
  validation {
    condition     = !var.enable_apply || length(var.entra_spa_client_id) > 0
    error_message = "entra_spa_client_id is required when enable_apply is true."
  }
}
variable "entra_api_client_id" {
  type        = string
  description = "Microsoft Entra API application client ID used as JWT audience."
  default     = ""
  validation {
    condition     = !var.enable_apply || length(var.entra_api_client_id) > 0
    error_message = "entra_api_client_id is required when enable_apply is true."
  }
}
variable "entra_operator_group_id" {
  type        = string
  description = "Entra group allowed to perform imports and allocation changes."
  default     = ""
  validation {
    condition     = !var.enable_apply || length(var.entra_operator_group_id) > 0
    error_message = "entra_operator_group_id is required when enable_apply is true."
  }
}
