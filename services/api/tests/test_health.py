import hashlib
import time

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from http.cookies import SimpleCookie

from app import main
from app.main import app


def _session_cookie_value(response) -> str:
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    return cookie["orhex_session"].value


def test_anonymous_session_cookie_is_created_without_a_configured_secret(monkeypatch) -> None:
    monkeypatch.delenv("ORHEX_SESSION_SECRET", raising=False)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    session_id = _session_cookie_value(response)
    assert session_id.startswith(main._SESSION_ID_PREFIX)
    assert len(session_id) == 46
    assert session_id.isascii()
    assert session_id not in response.text
    assert cookie["orhex_session"]["httponly"]
    assert cookie["orhex_session"]["samesite"].lower() == "lax"


def test_anonymous_session_persists_per_client_and_isolated_between_clients() -> None:
    with TestClient(app) as first_client, TestClient(app) as second_client:
        first_response = first_client.get("/health")
        repeated_response = first_client.get("/health")
        separate_response = second_client.get("/health")

    first_session_id = _session_cookie_value(first_response)
    assert _session_cookie_value(repeated_response) == first_session_id
    assert _session_cookie_value(separate_response) != first_session_id


def test_unrecognized_cookie_value_is_replaced_with_a_random_session_id() -> None:
    predictable_id = "not-a-session-id"
    with TestClient(app) as client:
        client.cookies.set("orhex_session", predictable_id)
        response = client.get("/health")

    assert _session_cookie_value(response) != predictable_id


def test_unmapped_legacy_session_fails_explicitly_without_replacing_cookie() -> None:
    legacy_id = "a" * 43
    with TestClient(app) as client:
        client.cookies.set("orhex_session", legacy_id)
        response = client.get("/health")

    assert response.status_code == 409
    assert "legacy session" in response.json()["detail"].lower()
    assert legacy_id not in response.text
    assert "set-cookie" not in response.headers


def test_legacy_session_keeps_its_original_namespace_while_mapping_exists() -> None:
    legacy_id = "a" * 43
    legacy_namespace_seed = "existing-walrus-session-seed"
    legacy_app = FastAPI()

    @legacy_app.get("/namespace")
    async def get_namespace(request: Request) -> dict[str, str]:
        return {"namespace": main._session_namespace(request)}

    middleware = main.OpaqueSessionMiddleware(legacy_app)
    middleware.sessions[legacy_id] = (
        time.monotonic() + 60,
        {"orhex_session": legacy_namespace_seed},
    )

    with TestClient(middleware) as client:
        client.cookies.set("orhex_session", legacy_id)
        response = client.get("/namespace")

    expected_namespace = (
        f"{main.MEMWAL_NAMESPACE[:107]}-"
        f"{hashlib.sha256(legacy_namespace_seed.encode('utf-8')).hexdigest()[:20]}"
    )
    assert response.status_code == 200
    assert response.json()["namespace"] == expected_namespace


def test_production_session_cookie_is_secure(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    production_app = FastAPI()
    production_app.add_middleware(
        main.OpaqueSessionMiddleware,
        cookie_secure=main._session_cookie_secure(),
    )

    with TestClient(production_app) as client:
        response = client.get("/")

    assert response.status_code == 404
    assert "secure" in response.headers["set-cookie"].lower()
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()


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
