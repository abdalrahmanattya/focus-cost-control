from fastapi.testclient import TestClient
from focus_cost.main import app, ROWS
import time
client=TestClient(app)
def setup_function(): ROWS[:] = [
 {"BillingPeriodStart":"2026-01-01","BillingPeriodEnd":"2026-01-31","ProviderName":"AWS","ServiceName":"Compute","BilledCost":1200.0,"Currency":"USD","Account":"prod","Workload":"orders"},
 {"BillingPeriodStart":"2026-01-01","BillingPeriodEnd":"2026-01-31","ProviderName":"Azure","ServiceName":"Database","BilledCost":800.0,"Currency":"USD","Account":"prod","Workload":"orders"},
 {"BillingPeriodStart":"2026-02-01","BillingPeriodEnd":"2026-02-28","ProviderName":"AWS","ServiceName":"Compute","BilledCost":1500.0,"Currency":"USD","Account":"prod","Workload":"orders"},
 {"BillingPeriodStart":"2026-02-01","BillingPeriodEnd":"2026-02-28","ProviderName":"Azure","ServiceName":"Database","BilledCost":840.0,"Currency":"USD","Account":"prod","Workload":"orders"},
 {"BillingPeriodStart":"2026-02-01","BillingPeriodEnd":"2026-02-28","ProviderName":"OpenAI","ServiceName":"Inference","BilledCost":400.0,"Currency":"USD","Account":"ai","Workload":"summaries"}]
def test_health_and_summary():
    assert client.get('/health').json()['status']=='ok'
    body=client.get('/api/v1/summary').json(); assert body['total']==4740.0 and body['forecast_next_month']==3480.0
def test_import_and_validation():
    csv='BillingPeriodStart,BillingPeriodEnd,ProviderName,ServiceName,BilledCost,Currency\n2026-03-01,2026-03-31,AWS,Storage,10,USD\n'
    r=client.post('/api/v1/imports',files={'file':('cost.csv',csv,'text/csv')}); assert r.status_code==202 and r.json()['records_inserted']==0 and r.json()['pending'] is True
    import_id = r.json()['import_id']
    for _ in range(100):
        status = client.get(f'/api/v1/imports/{import_id}').json()
        if status['status'] == 'completed': break
        time.sleep(0.001)
    assert status['records_inserted'] == 1
    assert client.post('/api/v1/allocations',json=[{'key':'platform','percent':100}]).status_code==200
def test_invalid_currency_and_negative_cost():
    csv='BillingPeriodStart,BillingPeriodEnd,ProviderName,ServiceName,BilledCost,Currency\n2026-03-01,2026-03-31,AWS,Storage,-1,EUR\n'
    assert client.post('/api/v1/imports',files={'file':('bad.csv',csv,'text/csv')}).status_code==422
