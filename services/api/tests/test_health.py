from fastapi.testclient import TestClient

from app import main
from app.main import app


def test_health_reports_api_liveness_without_claiming_provider_readiness() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "orhex-api"}


def test_provider_status_does_not_claim_unconfigured_providers_are_ready(monkeypatch) -> None:
    monkeypatch.setattr(main, "MEMWAL_PRIVATE_KEY", "")
    monkeypatch.setattr(main, "MEMWAL_ACCOUNT_ID", "")
    monkeypatch.setattr(main, "TATUM_API_KEY", "")
    with TestClient(app) as client:
        response = client.get("/integrations/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["walrus"]["status"] == "unavailable"
    assert payload["tatum"]["status"] == "unavailable"


def test_sui_lookup_rejects_malformed_address_before_provider_access() -> None:
    with TestClient(app) as client:
        response = client.get("/sui/wallet/not-an-address")

    assert response.status_code == 422


def test_memory_rejects_whitespace_only_input() -> None:
    with TestClient(app) as client:
        response = client.post("/memory/remember", json={"text": "   "})

    assert response.status_code == 422
