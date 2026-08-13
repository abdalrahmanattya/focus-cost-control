"""Azure Service Bus worker entrypoint for the Container Apps Job."""
from __future__ import annotations
import json
import os
from .domain import ImportRun
from .importer import parse_csv
from .repository import PostgresRepository

def main() -> None:
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient
    from azure.servicebus import ServiceBusClient
    repository = PostgresRepository(os.environ["DATABASE_URL"])
    credential = DefaultAzureCredential()
    blob_service = BlobServiceClient(account_url=os.environ["BLOB_ACCOUNT_URL"], credential=credential)
    namespace = os.environ["SERVICE_BUS_NAMESPACE"]
    with ServiceBusClient(fully_qualified_namespace=f"{namespace}.servicebus.windows.net", credential=credential) as client:
        with client.get_queue_receiver(queue_name=os.environ.get("SERVICE_BUS_QUEUE", "cost-imports"), max_wait_time=30) as receiver:
            for message in receiver:
                payload = None
                try:
                    payload = json.loads(str(message))
                    run = repository.get_import(payload["import_id"])
                    if run is None:
                        run = ImportRun(payload["import_id"], "processing")
                        repository.register_import(run)
                    run.status = "processing"
                    run.attempt += 1
                    repository.update_import(run.id, "processing", attempt=run.attempt, error=None)
                    blob = blob_service.get_blob_client(os.environ.get("BLOB_CONTAINER", "incoming"), payload["blob_name"])
                    records = parse_csv(blob.download_blob().readall())
                    run.records_received = len(records)
                    repository.save_import(run, records)
                    receiver.complete_message(message)
                except Exception as exc:
                    if payload and repository.get_import(payload.get("import_id")):
                        repository.update_import(payload["import_id"], "failed", error=str(exc))
                    if getattr(message, "delivery_count", 0) >= int(os.getenv("SERVICE_BUS_MAX_DELIVERY", "5")):
                        receiver.dead_letter_message(message, reason="processing_failed", error_description=str(exc)[:1024])
                        if payload:
                            repository.update_import(payload["import_id"], "dead_letter", error=str(exc))
                    else:
                        receiver.abandon_message(message)

if __name__ == "__main__": main()
