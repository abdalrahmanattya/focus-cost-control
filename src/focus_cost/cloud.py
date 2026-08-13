"""Azure adapters used only when the deployment supplies managed identity settings."""
from __future__ import annotations
import json
import os

def upload_and_enqueue(run_id: str, payload: bytes, filename: str) -> None:
    """Write an import to private Blob Storage and enqueue its pointer in Service Bus."""
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    credential = DefaultAzureCredential()
    account = os.environ["BLOB_ACCOUNT_URL"]
    container = os.environ.get("BLOB_CONTAINER", "incoming")
    blob_name = f"{run_id}/{filename}"
    blob = BlobServiceClient(account_url=account, credential=credential).get_blob_client(container, blob_name)
    blob.upload_blob(payload, overwrite=False)
    namespace = os.environ["SERVICE_BUS_NAMESPACE"]
    with ServiceBusClient(fully_qualified_namespace=f"{namespace}.servicebus.windows.net", credential=credential) as client:
        with client.get_queue_sender(os.environ.get("SERVICE_BUS_QUEUE", "cost-imports")) as sender:
            sender.send_messages(ServiceBusMessage(json.dumps({"import_id": run_id, "blob_name": blob_name})))
