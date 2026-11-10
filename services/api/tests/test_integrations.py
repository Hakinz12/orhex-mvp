import pytest
from fastapi import FastAPI, HTTPException
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app import main
from app.main import app


class FakeWalrusClient:
    def __init__(self) -> None:
        self.saved: dict[str, str] = {}
        self.idempotency_keys: dict[str, str] = {}
        self.recalled_namespaces: list[str] = []
        self.closed = False

    async def remember(self, text: str, namespace: str, idempotency_key: str):
        if idempotency_key in self.idempotency_keys:
            return SimpleNamespace(job_id=self.idempotency_keys[idempotency_key])
        job_id = f"job-{len(self.saved) + 1}"
        self.saved[job_id] = namespace
        self.idempotency_keys[idempotency_key] = job_id
        self.text = text
        return SimpleNamespace(job_id=job_id)

    async def get_remember_status(self, job_id: str):
        return SimpleNamespace(
            job_id=job_id,
            status="confirmed",
            blob_id=f"blob-{job_id}",
            namespace=self.saved[job_id],
            error=None,
        )

    async def recall(self, params):
        self.recalled_namespaces.append(params.namespace)
        return SimpleNamespace(
            results=[
                SimpleNamespace(
                    blob_id="blob-job-1",
                    text=self.text,
                    score=0.99,
                    created_at="2026-11-10T00:00:00Z",
                )
            ]
        )

    async def health(self):
        return SimpleNamespace(write_ready=True, status="ready")

    async def close(self):
        self.closed = True


def test_memory_isolation_confirmation_and_recall_are_session_scoped(monkeypatch) -> None:
    fake = FakeWalrusClient()
    monkeypatch.setattr(main, "MEMWAL_PRIVATE_KEY", "a" * 64)
    monkeypatch.setattr(main, "MEMWAL_ACCOUNT_ID", "0x" + "b" * 64)
    monkeypatch.setattr(main, "_walrus_client", lambda: fake)

    with TestClient(app) as first_session:
        saved = first_session.post(
            "/memory/remember",
            json={"text": "I prefer concise updates with clear next steps."},
        )
        session_id = first_session.cookies.get("orhex_session")
        assert saved.status_code == 200
        assert saved.json()["status"] == "confirmed"
        assert saved.json()["blob_id"] == "blob-job-1"
        assert session_id is not None
        assert session_id not in saved.text

        recalled = first_session.post(
            "/memory/recall",
            json={"query": "What is my update preference?"},
        )
        assert recalled.status_code == 200
        assert recalled.json()["results"][0]["text"] == fake.text
        assert first_session.cookies.get("orhex_session") == session_id

    with TestClient(app) as another_session:
        another_session_status = another_session.get("/memory/status/job-1")
        assert another_session.cookies.get("orhex_session") != session_id

    assert another_session_status.status_code == 404
    assert fake.closed


def test_memory_namespace_survives_a_new_application_instance(monkeypatch) -> None:
    fake = FakeWalrusClient()
    fake.text = "Existing session memory"
    monkeypatch.setattr(main, "MEMWAL_PRIVATE_KEY", "a" * 64)
    monkeypatch.setattr(main, "MEMWAL_ACCOUNT_ID", "0x" + "b" * 64)
    monkeypatch.setattr(main, "_walrus_client", lambda: fake)

    with TestClient(app) as original_instance:
        original_recall = original_instance.post(
            "/memory/recall",
            json={"query": "Find existing memory"},
        )
        session_id = original_instance.cookies.get("orhex_session")

    assert original_recall.status_code == 200
    assert session_id is not None
    original_namespace = original_recall.json()["namespace"]
    restarted_app = FastAPI()
    restarted_app.include_router(app.router)
    restarted_app.add_middleware(
        main.OpaqueSessionMiddleware,
        cookie_secure=False,
    )
    with TestClient(restarted_app) as restarted_instance:
        restarted_instance.cookies.set("orhex_session", session_id)
        restarted_recall = restarted_instance.post(
            "/memory/recall",
            json={"query": "Find existing memory"},
        )

    assert restarted_recall.status_code == 200
    assert restarted_recall.json()["namespace"] == original_namespace
    assert session_id not in restarted_recall.text
    assert fake.recalled_namespaces == [original_namespace, original_namespace]


def test_walrus_confirmation_without_blob_id_is_not_reported_as_confirmed(monkeypatch) -> None:
    fake = FakeWalrusClient()
    monkeypatch.setattr(main, "MEMWAL_PRIVATE_KEY", "a" * 64)
    monkeypatch.setattr(main, "MEMWAL_ACCOUNT_ID", "0x" + "b" * 64)
    monkeypatch.setattr(main, "_walrus_client", lambda: fake)
    fake.get_remember_status = async_no_blob_status

    with TestClient(app) as client:
        response = client.post(
            "/memory/remember",
            json={"text": "Remember the weekly project planning session."},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "reconciliation_required"
    assert response.json()["blob_id"] is None


def test_memory_idempotency_key_prevents_duplicate_provider_writes(monkeypatch) -> None:
    fake = FakeWalrusClient()
    monkeypatch.setattr(main, "MEMWAL_PRIVATE_KEY", "a" * 64)
    monkeypatch.setattr(main, "MEMWAL_ACCOUNT_ID", "0x" + "b" * 64)
    monkeypatch.setattr(main, "_walrus_client", lambda: fake)
    payload = {
        "text": "Remember the weekly project planning session.",
        "idempotency_key": "11111111-1111-4111-8111-111111111111",
    }

    with TestClient(app) as client:
        first = client.post("/memory/remember", json=payload)
        retry = client.post("/memory/remember", json=payload)

    assert first.json()["job_id"] == retry.json()["job_id"]
    assert len(fake.saved) == 1


async def async_no_blob_status(job_id: str):
    return SimpleNamespace(
        job_id=job_id,
        status="confirmed",
        blob_id=None,
        namespace="orhex-personal-memory-test",
        error=None,
    )


def test_sui_lookup_returns_provider_data_after_chain_identity_check(monkeypatch) -> None:
    async def fake_query(query: str, variables: dict):
        assert variables == {"address": "0x1234"}
        return {
            "chainIdentifier": main._SUI_MAINNET_CHAIN,
            "address": {
                "balance": {"totalBalance": "2500000000"},
                "transactions": {
                    "nodes": [
                        {
                            "digest": "actual-provider-digest",
                            "effects": {"timestamp": None, "status": "success"},
                        }
                    ]
                },
            },
            "checkpoints": {"nodes": [{"sequenceNumber": "123"}]},
        }

    monkeypatch.setattr(main, "_tatum_query", fake_query)
    with TestClient(app) as client:
        response = client.get("/sui/wallet/1234")

    assert response.status_code == 200
    assert response.json()["address"] == "0x1234"
    assert response.json()["source"] == "Tatum Sui GraphQL"
    assert response.json()["balance_sui"] == "2.5000"
    assert response.json()["latest_checkpoint"] == 123
    assert response.json()["activity"][0]["digest"] == "actual-provider-digest"


def test_tatum_query_rejects_a_mismatched_network_identity(monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"data": {"chainIdentifier": "unexpected-chain"}}

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return FakeResponse()

    monkeypatch.setattr(main, "TATUM_API_KEY", "test-only")
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)

    with pytest.raises(HTTPException) as error:
        import asyncio

        asyncio.run(main._tatum_query("query { chainIdentifier }", {}))

    assert error.value.status_code == 502
    assert "identity" in str(error.value.detail)
