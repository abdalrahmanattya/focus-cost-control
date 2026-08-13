from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_cloud_edge_and_private_dependency_contracts_are_explicit():
    terraform = (ROOT / "infra/azure/main.tf").read_text()
    assert "internal_load_balancer_enabled = false" in terraform
    assert 'external_enabled           = false' in terraform
    assert 'external_enabled           = true' in terraform
    assert 'public_network_access_enabled   = false' in terraform
    assert 'public_network_access_enabled = false' in terraform
    assert 'resource "azurerm_private_endpoint" "blob"' in terraform
    assert 'resource "azurerm_private_endpoint" "servicebus"' in terraform
    assert 'privatelink.blob.core.windows.net' in terraform
    assert 'privatelink.servicebus.windows.net' in terraform
    assert 'variable "entra_spa_client_id"' in (ROOT / "infra/azure/variables.tf").read_text()
    assert 'variable "entra_api_client_id"' in (ROOT / "infra/azure/variables.tf").read_text()


def test_local_web_proxy_and_non_root_runtime_contract():
    compose = (ROOT / "compose.yaml").read_text()
    dockerfile = (ROOT / "web/Dockerfile").read_text()
    nginx = (ROOT / "web/nginx.conf.template").read_text()
    assert 'API_INTERNAL_HOST=api:8000' in compose
    assert 'API_INTERNAL_SCHEME=http' in compose
    assert ':8080' in compose and 'listen 8080' in nginx
    assert 'USER 101' in dockerfile
    assert 'nginx-unprivileged' in dockerfile
