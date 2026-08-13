from __future__ import annotations

import os
from functools import lru_cache
from decimal import Decimal
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .analytics import allocations as calculate_allocations, summary as calculate_summary, variance as calculate_variance
from .domain import ValidationError
from .domain import ImportRun
from .importer import parse_csv
from .jobs import ImportWorker
from .repository import get_repository
from uuid import uuid4

ROWS = [
 {"BillingPeriodStart":"2026-01-01","BillingPeriodEnd":"2026-01-31","ProviderName":"AWS","ServiceName":"Compute","BilledCost":1200.0,"Currency":"USD","Account":"prod","Workload":"orders"},
 {"BillingPeriodStart":"2026-01-01","BillingPeriodEnd":"2026-01-31","ProviderName":"Azure","ServiceName":"Database","BilledCost":800.0,"Currency":"USD","Account":"prod","Workload":"orders"},
 {"BillingPeriodStart":"2026-02-01","BillingPeriodEnd":"2026-02-28","ProviderName":"AWS","ServiceName":"Compute","BilledCost":1500.0,"Currency":"USD","Account":"prod","Workload":"orders"},
 {"BillingPeriodStart":"2026-02-01","BillingPeriodEnd":"2026-02-28","ProviderName":"Azure","ServiceName":"Database","BilledCost":840.0,"Currency":"USD","Account":"prod","Workload":"orders"},
 {"BillingPeriodStart":"2026-02-01","BillingPeriodEnd":"2026-02-28","ProviderName":"OpenAI","ServiceName":"Inference","BilledCost":400.0,"Currency":"USD","Account":"ai","Workload":"summaries"},
]

app = FastAPI(title="Focus Cost Control", version="1.0.0", description="Deterministic FOCUS 1.4 subset cost intelligence")
app.add_middleware(CORSMiddleware, allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","), allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])

@lru_cache(maxsize=1)
def _jwks_client():
    from jwt import PyJWKClient
    return PyJWKClient(os.environ["AUTH_JWKS_URL"])

def _claims(authorization: str | None) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Bearer token required", headers={"WWW-Authenticate": "Bearer"})
    import jwt
    token = authorization.split(" ", 1)[1]
    signing_key = _jwks_client().get_signing_key_from_jwt(token).key
    return jwt.decode(token, signing_key, algorithms=["RS256"], audience=os.environ["AUTH_AUDIENCE"], issuer=os.environ["AUTH_ISSUER"])

@app.middleware("http")
async def require_azure_auth(request, call_next):
    if os.getenv("AUTH_REQUIRED", "false").lower() != "true" or request.url.path == "/health":
        return await call_next(request)
    try:
        claims = _claims(request.headers.get("authorization"))
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            groups = claims.get("groups", [])
            if os.getenv("AUTH_OPERATOR_GROUP_ID") not in groups:
                return JSONResponse({"detail": "operator role required"}, status_code=403)
        request.state.claims = claims
        return await call_next(request)
    except HTTPException as exc:
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)
    except Exception:
        return JSONResponse({"detail": "invalid bearer token"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})

from fastapi.responses import JSONResponse
repository = get_repository(ROWS)
worker = ImportWorker(repository)
_memory_rows_count = len(ROWS)

class Allocation(BaseModel):
    key: str = Field(min_length=1, max_length=128)
    percent: float = Field(ge=0, le=100)

class UnitMetric(BaseModel):
    metric_key: str = Field(min_length=1, max_length=128)
    period_start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    volume: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=64)
    source: str = Field(default="declared", max_length=64)

def _records():
    # Keep the legacy exported ROWS fixture useful for isolated test resets while
    # retaining imported rows in the actual repository.
    global repository, worker, _memory_rows_count
    if not os.getenv("DATABASE_URL") and len(ROWS) < _memory_rows_count:
        repository = get_repository(ROWS)
        worker = ImportWorker(repository)
    _memory_rows_count = len(ROWS)
    return repository.records()
def _unit_volume() -> Decimal:
    metrics = [m for m in repository.unit_metrics() if m["metric_key"] == "orders"]
    return Decimal(str(metrics[0]["volume"])) if metrics else Decimal("10000")
def _error(exc: ValidationError): raise HTTPException(status_code=422, detail={"message": str(exc), **exc.details})

@app.get("/health")
def health():
    return {"status": "ok", "service": "focus-cost-control", "database": bool(os.getenv("DATABASE_URL")), "queue": worker.queue.qsize(), "dead_letter": len(worker.dead_letter)}

@app.get("/api/v1/summary")
def summary():
    result = calculate_summary(_records(), _unit_volume())
    repository.save_report("summary", result)
    return result

@app.get("/api/v1/records")
@app.get("/api/v1/costs")
def records():
    items = [r.as_dict() for r in _records()]
    return {"count": len(items), "items": items}

@app.post("/api/v1/imports", status_code=202)
async def import_csv(file: UploadFile = File(...)):
    global _memory_rows_count
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "CSV file required")
    try:
        raw = await file.read()
        parsed = parse_csv(raw)
    except ValidationError as exc: _error(exc)
    if os.getenv("SERVICE_BUS_NAMESPACE") and os.getenv("BLOB_ACCOUNT_URL"):
        # Cloud deployments use Blob + Service Bus and a queue-triggered Container Apps Job.
        run = ImportRun(str(uuid4()), "queued", len(parsed))
        repository.register_import(run)
        from .cloud import upload_and_enqueue
        upload_and_enqueue(run.id, raw, file.filename)
    else:
        if not os.getenv("DATABASE_URL"):
            ROWS.extend(record.as_dict() for record in parsed)
            _memory_rows_count = len(ROWS)
        run = worker.enqueue(parsed)
    return {"status": "accepted", "import_id": run.id, "records_received": len(parsed), "records_inserted": 0, "records_updated": 0, "pending": True, "format": "FOCUS 1.4 subset"}

@app.get("/api/v1/imports")
def imports():
    return {"items": [run.as_dict() for run in repository.list_imports()], "queue_depth": worker.queue.qsize(), "dead_letter_count": len(worker.dead_letter)}

@app.get("/api/v1/imports/{import_id}")
def import_status(import_id: str):
    run = repository.get_import(import_id)
    if run is None:
        for job in worker.dead_letter:
            if job.run.id == import_id: run = job.run
    if run is None:
        # queued jobs are not persisted until processing; expose a stable 202 response where possible.
        raise HTTPException(404, "import run not found")
    return run.as_dict()

@app.post("/api/v1/allocations")
def save_allocations(items: list[Allocation]):
    rules = [item.model_dump() for item in items]
    if abs(sum(item.percent for item in items) - 100) > 1e-6:
        raise HTTPException(422, "allocation percentages must total 100")
    repository.save_rules(rules)
    return {"status": "validated", **calculate_allocations(_records(), rules)}

@app.get("/api/v1/allocations")
def get_allocations():
    rules = repository.rules()
    return {"rules": rules, **calculate_allocations(_records(), rules)} if rules else {"rules": [], "allocations": []}

@app.get("/api/v1/forecasts")
def forecasts():
    result = calculate_summary(_records())
    return {"forecast_next_month": result["forecast_next_month"], "monthly": result["monthly"], "method": "latest period plus latest period delta"}

@app.get("/api/v1/variance")
def variance(): return calculate_variance(_records())

@app.get("/api/v1/anomalies")
def anomalies(): return {"items": calculate_summary(_records())["anomalies"]}

@app.get("/api/v1/unit-economics")
def unit_economics(): return calculate_summary(_records(), _unit_volume())["unit_economics"]

@app.get("/api/v1/unit-metrics")
def get_unit_metrics(): return {"items": repository.unit_metrics()}

@app.post("/api/v1/unit-metrics", status_code=201)
def save_unit_metric(metric: UnitMetric):
    repository.save_unit_metric(metric.model_dump())
    return {"status": "saved", "metric": metric.model_dump()}

@app.get("/api/v1/reports")
def reports(): return {"items": repository.reports()}
