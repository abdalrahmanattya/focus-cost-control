data "azurerm_client_config" "current" {}

resource "azurerm_virtual_network" "this" {
  count               = var.enable_apply ? 1 : 0
  name                = "${var.name}-vnet"
  location            = var.location
  resource_group_name = azurerm_resource_group.this[0].name
  address_space       = ["10.40.0.0/16"]
}

resource "azurerm_subnet" "apps" {
  count                = var.enable_apply ? 1 : 0
  name                 = "apps"
  resource_group_name  = azurerm_resource_group.this[0].name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = ["10.40.0.0/23"]
  delegation {
    name = "container-apps"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "postgres" {
  count                = var.enable_apply ? 1 : 0
  name                 = "postgres"
  resource_group_name  = azurerm_resource_group.this[0].name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = ["10.40.2.0/28"]
  delegation {
    name = "postgres-flexible-server"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_subnet" "private_endpoints" {
  count                = var.enable_apply ? 1 : 0
  name                 = "private-endpoints"
  resource_group_name  = azurerm_resource_group.this[0].name
  virtual_network_name = azurerm_virtual_network.this[0].name
  address_prefixes     = ["10.40.3.0/24"]
}

resource "azurerm_private_dns_zone" "postgres" {
  count               = var.enable_apply ? 1 : 0
  name                = "private.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.this[0].name
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  count                 = var.enable_apply ? 1 : 0
  name                  = "${var.name}-postgres-dns-link"
  resource_group_name   = azurerm_resource_group.this[0].name
  private_dns_zone_name = azurerm_private_dns_zone.postgres[0].name
  virtual_network_id    = azurerm_virtual_network.this[0].id
}

resource "azurerm_private_dns_zone" "blob" {
  count               = var.enable_apply ? 1 : 0
  name                = "privatelink.blob.core.windows.net"
  resource_group_name = azurerm_resource_group.this[0].name
}

resource "azurerm_private_dns_zone" "servicebus" {
  count               = var.enable_apply ? 1 : 0
  name                = "privatelink.servicebus.windows.net"
  resource_group_name = azurerm_resource_group.this[0].name
}

resource "azurerm_private_dns_zone_virtual_network_link" "blob" {
  count                 = var.enable_apply ? 1 : 0
  name                  = "${var.name}-blob-dns-link"
  resource_group_name   = azurerm_resource_group.this[0].name
  private_dns_zone_name = azurerm_private_dns_zone.blob[0].name
  virtual_network_id    = azurerm_virtual_network.this[0].id
}

resource "azurerm_private_dns_zone_virtual_network_link" "servicebus" {
  count                 = var.enable_apply ? 1 : 0
  name                  = "${var.name}-servicebus-dns-link"
  resource_group_name   = azurerm_resource_group.this[0].name
  private_dns_zone_name = azurerm_private_dns_zone.servicebus[0].name
  virtual_network_id    = azurerm_virtual_network.this[0].id
}

resource "azurerm_resource_group" "this" {
  count    = var.enable_apply ? 1 : 0
  name     = var.name
  location = var.location
}

resource "azurerm_log_analytics_workspace" "this" {
  count               = var.enable_apply ? 1 : 0
  name                = "${var.name}-logs"
  location            = var.location
  resource_group_name = azurerm_resource_group.this[0].name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "this" {
  count               = var.enable_apply ? 1 : 0
  name                = "${var.name}-ai"
  location            = var.location
  resource_group_name = azurerm_resource_group.this[0].name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.this[0].id
}

resource "azurerm_container_app_environment" "this" {
  count                          = var.enable_apply ? 1 : 0
  name                           = "${var.name}-env"
  location                       = var.location
  resource_group_name            = azurerm_resource_group.this[0].name
  log_analytics_workspace_id     = azurerm_log_analytics_workspace.this[0].id
  infrastructure_subnet_id       = azurerm_subnet.apps[0].id
  internal_load_balancer_enabled = false
}

resource "azurerm_storage_account" "imports" {
  count                           = var.enable_apply ? 1 : 0
  name                            = substr(replace(lower("${var.name}imports"), "-", ""), 0, 24)
  resource_group_name             = azurerm_resource_group.this[0].name
  location                        = var.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  public_network_access_enabled   = false
  blob_properties { versioning_enabled = true }
}

resource "azurerm_storage_container" "incoming" {
  count                 = var.enable_apply ? 1 : 0
  name                  = "incoming"
  storage_account_id    = azurerm_storage_account.imports[0].id
  container_access_type = "private"
}

resource "azurerm_private_endpoint" "blob" {
  count               = var.enable_apply ? 1 : 0
  name                = "${var.name}-blob-private-endpoint"
  location            = var.location
  resource_group_name = azurerm_resource_group.this[0].name
  subnet_id           = azurerm_subnet.private_endpoints[0].id
  private_service_connection {
    name                           = "${var.name}-blob-connection"
    private_connection_resource_id = azurerm_storage_account.imports[0].id
    is_manual_connection           = false
    subresource_names              = ["blob"]
  }
  private_dns_zone_group {
    name                 = "blob-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.blob[0].id]
  }
}

resource "azurerm_servicebus_namespace" "this" {
  count                         = var.enable_apply ? 1 : 0
  name                          = "${var.name}-bus"
  location                      = var.location
  resource_group_name           = azurerm_resource_group.this[0].name
  sku                           = "Standard"
  minimum_tls_version           = "1.2"
  public_network_access_enabled = false
}

resource "azurerm_servicebus_queue" "imports" {
  count                                = var.enable_apply ? 1 : 0
  name                                 = "cost-imports"
  namespace_id                         = azurerm_servicebus_namespace.this[0].id
  dead_lettering_on_message_expiration = true
  max_delivery_count                   = 5
  lock_duration                        = "PT5M"
}

resource "azurerm_private_endpoint" "servicebus" {
  count               = var.enable_apply ? 1 : 0
  name                = "${var.name}-servicebus-private-endpoint"
  location            = var.location
  resource_group_name = azurerm_resource_group.this[0].name
  subnet_id           = azurerm_subnet.private_endpoints[0].id
  private_service_connection {
    name                           = "${var.name}-servicebus-connection"
    private_connection_resource_id = azurerm_servicebus_namespace.this[0].id
    is_manual_connection           = false
    subresource_names              = ["namespace"]
  }
  private_dns_zone_group {
    name                 = "servicebus-dns"
    private_dns_zone_ids = [azurerm_private_dns_zone.servicebus[0].id]
  }
}

resource "azurerm_postgresql_flexible_server" "this" {
  count                         = var.enable_apply ? 1 : 0
  name                          = "${var.name}-pg"
  resource_group_name           = azurerm_resource_group.this[0].name
  location                      = var.location
  version                       = "16"
  administrator_login           = var.postgres_admin_login
  administrator_password        = var.postgres_admin_password
  storage_mb                    = 32768
  sku_name                      = "B_Standard_B1ms"
  public_network_access_enabled = false
  backup_retention_days         = 7
  delegated_subnet_id           = azurerm_subnet.postgres[0].id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres[0].id
  depends_on                    = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

resource "azurerm_postgresql_flexible_server_database" "focus" {
  count     = var.enable_apply ? 1 : 0
  name      = "focus"
  server_id = azurerm_postgresql_flexible_server.this[0].id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_key_vault" "this" {
  count                      = var.enable_apply ? 1 : 0
  name                       = substr("${var.name}-kv", 0, 24)
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this[0].name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
  rbac_authorization_enabled = true
}

resource "azurerm_role_assignment" "deployer_key_vault" {
  count                = var.enable_apply ? 1 : 0
  scope                = azurerm_key_vault.this[0].id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_key_vault_secret" "postgres_connection" {
  count        = var.enable_apply ? 1 : 0
  name         = "postgres-connection"
  value        = "postgresql://${var.postgres_admin_login}:${var.postgres_admin_password}@${azurerm_postgresql_flexible_server.this[0].fqdn}:5432/focus?sslmode=require"
  key_vault_id = azurerm_key_vault.this[0].id
  depends_on   = [azurerm_role_assignment.deployer_key_vault]
}

resource "azurerm_user_assigned_identity" "api" {
  count               = var.enable_apply ? 1 : 0
  name                = "${var.name}-api"
  location            = var.location
  resource_group_name = azurerm_resource_group.this[0].name
}

resource "azurerm_user_assigned_identity" "worker" {
  count               = var.enable_apply ? 1 : 0
  name                = "${var.name}-worker"
  location            = var.location
  resource_group_name = azurerm_resource_group.this[0].name
}

resource "azurerm_role_assignment" "api_blob" {
  count                = var.enable_apply ? 1 : 0
  scope                = azurerm_storage_account.imports[0].id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.api[0].principal_id
}
resource "azurerm_role_assignment" "worker_blob" {
  count                = var.enable_apply ? 1 : 0
  scope                = azurerm_storage_account.imports[0].id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_user_assigned_identity.worker[0].principal_id
}
resource "azurerm_role_assignment" "api_bus" {
  count                = var.enable_apply ? 1 : 0
  scope                = azurerm_servicebus_queue.imports[0].id
  role_definition_name = "Azure Service Bus Data Sender"
  principal_id         = azurerm_user_assigned_identity.api[0].principal_id
}
resource "azurerm_role_assignment" "worker_bus" {
  count                = var.enable_apply ? 1 : 0
  scope                = azurerm_servicebus_queue.imports[0].id
  role_definition_name = "Azure Service Bus Data Receiver"
  principal_id         = azurerm_user_assigned_identity.worker[0].principal_id
}
resource "azurerm_role_assignment" "api_secrets" {
  count                = var.enable_apply ? 1 : 0
  scope                = azurerm_key_vault.this[0].id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.api[0].principal_id
}
resource "azurerm_role_assignment" "worker_secrets" {
  count                = var.enable_apply ? 1 : 0
  scope                = azurerm_key_vault.this[0].id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.worker[0].principal_id
}

resource "azurerm_container_app" "api" {
  count                        = var.enable_apply ? 1 : 0
  name                         = "${var.name}-api"
  container_app_environment_id = azurerm_container_app_environment.this[0].id
  resource_group_name          = azurerm_resource_group.this[0].name
  revision_mode                = "Single"
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api[0].id]
  }
  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.postgres_connection[0].versionless_id
    identity            = azurerm_user_assigned_identity.api[0].id
  }
  template {
    min_replicas = 0
    max_replicas = 3
    container {
      name   = "api"
      image  = var.container_image
      cpu    = 0.5
      memory = "1Gi"
      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "SERVICE_BUS_NAMESPACE"
        value = azurerm_servicebus_namespace.this[0].name
      }
      env {
        name  = "SERVICE_BUS_QUEUE"
        value = azurerm_servicebus_queue.imports[0].name
      }
      env {
        name  = "BLOB_ACCOUNT_URL"
        value = azurerm_storage_account.imports[0].primary_blob_endpoint
      }
      env {
        name  = "BLOB_CONTAINER"
        value = azurerm_storage_container.incoming[0].name
      }
      env {
        name  = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        value = azurerm_application_insights.this[0].connection_string
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.api[0].client_id
      }
      env {
        name  = "AUTH_REQUIRED"
        value = "true"
      }
      env {
        name  = "AUTH_ISSUER"
        value = "https://login.microsoftonline.com/${var.entra_tenant_id}/v2.0"
      }
      env {
        name  = "AUTH_JWKS_URL"
        value = "https://login.microsoftonline.com/${var.entra_tenant_id}/discovery/v2.0/keys"
      }
      env {
        name  = "AUTH_AUDIENCE"
        value = var.entra_api_client_id
      }
      env {
        name  = "AUTH_OPERATOR_GROUP_ID"
        value = var.entra_operator_group_id
      }
      liveness_probe {
        transport        = "HTTP"
        port             = 8000
        path             = "/health"
        interval_seconds = 30
      }
      readiness_probe {
        transport        = "HTTP"
        port             = 8000
        path             = "/health"
        interval_seconds = 10
      }
    }
  }
  ingress {
    external_enabled           = false
    allow_insecure_connections = false
    target_port                = 8000
    transport                  = "http"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

resource "azurerm_container_app" "web" {
  count                        = var.enable_apply ? 1 : 0
  name                         = "${var.name}-web"
  container_app_environment_id = azurerm_container_app_environment.this[0].id
  resource_group_name          = azurerm_resource_group.this[0].name
  revision_mode                = "Single"
  template {
    min_replicas = 1
    max_replicas = 2
    container {
      name   = "web"
      image  = var.web_image
      cpu    = 0.25
      memory = "0.5Gi"
      env {
        name  = "FOCUS_API_BASE"
        value = ""
      }
      env {
        name  = "API_INTERNAL_HOST"
        value = azurerm_container_app.api[0].ingress[0].fqdn
      }
      env {
        name  = "API_INTERNAL_SCHEME"
        value = "https"
      }
      env {
        name  = "FOCUS_AUTH_MODE"
        value = "cloud"
      }
      env {
        name  = "FOCUS_ENTRA_CLIENT_ID"
        value = var.entra_spa_client_id
      }
      env {
        name  = "FOCUS_ENTRA_TENANT_ID"
        value = var.entra_tenant_id
      }
      env {
        name  = "FOCUS_ENTRA_API_SCOPE"
        value = "api://${var.entra_api_client_id}/user_impersonation"
      }
      liveness_probe {
        transport        = "HTTP"
        port             = 8080
        path             = "/"
        interval_seconds = 30
      }
      readiness_probe {
        transport        = "HTTP"
        port             = 8080
        path             = "/"
        interval_seconds = 10
      }
    }
  }
  ingress {
    external_enabled           = true
    allow_insecure_connections = false
    target_port                = 8080
    transport                  = "http"
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}

resource "azurerm_container_app_job" "worker" {
  count                        = var.enable_apply ? 1 : 0
  name                         = "${var.name}-worker"
  location                     = var.location
  resource_group_name          = azurerm_resource_group.this[0].name
  container_app_environment_id = azurerm_container_app_environment.this[0].id
  replica_timeout_in_seconds   = 1800
  replica_retry_limit          = 3
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.worker[0].id]
  }
  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.postgres_connection[0].versionless_id
    identity            = azurerm_user_assigned_identity.worker[0].id
  }
  event_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
    scale {
      min_executions              = 0
      max_executions              = 3
      polling_interval_in_seconds = 30
      rules {
        name             = "cost-imports"
        custom_rule_type = "azure-servicebus"
        identity_id      = azurerm_user_assigned_identity.worker[0].id
        metadata         = { namespace = azurerm_servicebus_namespace.this[0].name, queueName = azurerm_servicebus_queue.imports[0].name, messageCount = "1" }
      }
    }
  }
  template {
    container {
      name    = "worker"
      image   = var.container_image
      cpu     = 0.5
      memory  = "1Gi"
      command = ["python", "-m", "focus_cost.worker"]
      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "SERVICE_BUS_NAMESPACE"
        value = azurerm_servicebus_namespace.this[0].name
      }
      env {
        name  = "SERVICE_BUS_QUEUE"
        value = azurerm_servicebus_queue.imports[0].name
      }
      env {
        name  = "BLOB_ACCOUNT_URL"
        value = azurerm_storage_account.imports[0].primary_blob_endpoint
      }
      env {
        name  = "BLOB_CONTAINER"
        value = azurerm_storage_container.incoming[0].name
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.worker[0].client_id
      }
    }
  }
}

resource "azurerm_container_app_job" "migration" {
  count                        = var.enable_apply ? 1 : 0
  name                         = "${var.name}-migration"
  location                     = var.location
  resource_group_name          = azurerm_resource_group.this[0].name
  container_app_environment_id = azurerm_container_app_environment.this[0].id
  replica_timeout_in_seconds   = 900
  replica_retry_limit          = 1
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.worker[0].id]
  }
  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.postgres_connection[0].versionless_id
    identity            = azurerm_user_assigned_identity.worker[0].id
  }
  manual_trigger_config {
    parallelism              = 1
    replica_completion_count = 1
  }
  template {
    container {
      name    = "migration"
      image   = var.container_image
      cpu     = 0.25
      memory  = "0.5Gi"
      command = ["sh", "scripts/migrate.sh"]
      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.worker[0].client_id
      }
    }
  }
}

output "api_url" { value = var.enable_apply ? "https://${azurerm_container_app.api[0].ingress[0].fqdn}" : null }
output "web_url" { value = var.enable_apply ? "https://${azurerm_container_app.web[0].ingress[0].fqdn}" : null }
output "resource_group" { value = try(azurerm_resource_group.this[0].name, null) }
output "storage_account" { value = try(azurerm_storage_account.imports[0].name, null) }
output "service_bus_queue" { value = try(azurerm_servicebus_queue.imports[0].name, null) }
output "key_vault" { value = try(azurerm_key_vault.this[0].name, null) }
output "postgres_server" { value = try(azurerm_postgresql_flexible_server.this[0].name, null) }
output "migration_job" { value = try(azurerm_container_app_job.migration[0].name, null) }
