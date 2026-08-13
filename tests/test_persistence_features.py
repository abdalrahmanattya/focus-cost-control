from fastapi.testclient import TestClient
from focus_cost.main import app
import jwt
from datetime import datetime, timedelta, timezone
from cryptography.hazmat.primitives.asymmetric import rsa

client = TestClient(app)

def test_unit_metric_and_report_snapshot():
    response = client.post('/api/v1/unit-metrics', json={'metric_key': 'orders', 'period_start': '2026-03-01', 'volume': 2000, 'unit': 'orders'})
    assert response.status_code == 201
    assert client.get('/api/v1/unit-metrics').json()['items'][0]['volume'] == 2000
    assert client.get('/api/v1/summary').status_code == 200
    assert client.get('/api/v1/reports').json()['items']

def test_auth_boundary_can_be_enabled(monkeypatch):
    monkeypatch.setenv('AUTH_REQUIRED', 'true')
    response = client.get('/api/v1/summary')
    assert response.status_code == 401
    monkeypatch.setenv('AUTH_REQUIRED', 'false')

def test_auth_accepts_only_valid_issuer_audience_and_operator_group(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = key.public_key()
    class SigningKey:
        def __init__(self, value): self.key = value
    class LocalJwks:
        def get_signing_key_from_jwt(self, token): return SigningKey(public)
    monkeypatch.setattr('focus_cost.main._jwks_client', lambda: LocalJwks())
    monkeypatch.setenv('AUTH_REQUIRED', 'true')
    monkeypatch.setenv('AUTH_ISSUER', 'https://issuer.test')
    monkeypatch.setenv('AUTH_AUDIENCE', 'api-client')
    monkeypatch.setenv('AUTH_OPERATOR_GROUP_ID', 'operators')
    def token(**overrides):
        claims = {'iss': 'https://issuer.test', 'aud': 'api-client', 'sub': 'user', 'exp': datetime.now(timezone.utc) + timedelta(minutes=5), 'groups': ['operators']}
        claims.update(overrides)
        return jwt.encode(claims, key, algorithm='RS256')
    assert client.get('/api/v1/summary', headers={'Authorization': f'Bearer {token()}'}).status_code == 200
    assert client.post('/api/v1/allocations', json=[{'key': 'platform', 'percent': 100}], headers={'Authorization': f'Bearer {token()}'}).status_code == 200
    assert client.post('/api/v1/allocations', json=[{'key': 'platform', 'percent': 100}], headers={'Authorization': f'Bearer {token(groups=[])}'}).status_code == 403
    assert client.get('/api/v1/summary', headers={'Authorization': f'Bearer {token(iss="https://evil.test")}'}).status_code == 401
    assert client.get('/api/v1/summary', headers={'Authorization': f'Bearer {token(aud="other-api")}'}).status_code == 401
    assert client.get('/api/v1/summary', headers={'Authorization': f'Bearer {token(exp=datetime.now(timezone.utc) - timedelta(minutes=1))}'}).status_code == 401
    monkeypatch.setenv('AUTH_REQUIRED', 'false')
