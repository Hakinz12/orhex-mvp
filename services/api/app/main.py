import hashlib
import logging
import os
import re
import secrets
import time
from threading import Lock
from typing import Any
from uuid import UUID, uuid4
from decimal import Decimal
from pathlib import Path

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from memwal import MemWal, RecallParams, MemWalError
from pydantic import BaseModel, Field, field_validator
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

load_dotenv(Path(__file__).resolve().parents[3] / ".env")
logger = logging.getLogger("orhex.api")
MEMWAL_SERVER_URL = os.getenv("MEMWAL_SERVER_URL") or "https://relayer.memory.walrus.xyz"
MEMWAL_ACCOUNT_ID = os.getenv("MEMWAL_ACCOUNT_ID", "")
MEMWAL_PRIVATE_KEY = os.getenv("MEMWAL_PRIVATE_KEY", "")
MEMWAL_NAMESPACE = os.getenv("MEMWAL_NAMESPACE") or "orhex-personal-memory"
TATUM_API_KEY = os.getenv("TATUM_API_KEY", "")
TATUM_SUI_RPC_URL = (os.getenv("TATUM_SUI_RPC_URL") or "https://sui-mainnet.gateway.tatum.io").rstrip("/")
SUI_NETWORK = (os.getenv("SUI_NETWORK") or "mainnet").lower()
_SUI_MAINNET_CHAIN = "4btiuiMPvEENsttpZC7CZ53DruC3MAgfznDbASZ7DR6S"
_SUI_TESTNET_CHAIN = "69WiPg3DAQiwdxfncX6wYQ2siKwAe6L9BZthQea3JNMD"
_SESSION_COOKIE_NAME = "orhex_session"
_SESSION_MAX_AGE = 14 * 24 * 60 * 60
_SESSION_ID_PREFIX = "v2_"
_SESSION_ID_PATTERN = re.compile(r"v2_[A-Za-z0-9_-]{43}")
_LEGACY_SESSION_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}")

app = FastAPI(title="ORHEX API", version="0.1.0")
origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def _session_cookie_secure() -> bool:
    return os.getenv("APP_ENV", "development").lower() == "production"


class OpaqueSessionMiddleware:
    def __init__(self, app: ASGIApp, cookie_secure: bool = False) -> None:
        self.app = app
        self.cookie_secure = cookie_secure
        self.sessions: dict[str, tuple[float, dict[str, Any]]] = {}
        self.sessions_lock = Lock()
        self.request_count = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        candidate_id = Request(scope).cookies.get(_SESSION_COOKIE_NAME, "")
        now = time.monotonic()
        legacy_session_unavailable = False
        with self.sessions_lock:
            session_entry = self.sessions.get(candidate_id)
            if _SESSION_ID_PATTERN.fullmatch(candidate_id):
                session_id = candidate_id
                session_data = (
                    session_entry[1]
                    if session_entry is not None and session_entry[0] > now
                    else {"orhex_session": session_id}
                )
            elif _LEGACY_SESSION_ID_PATTERN.fullmatch(candidate_id):
                if session_entry is None or session_entry[0] <= now:
                    legacy_session_unavailable = True
                    session_id = candidate_id
                    session_data = {}
                else:
                    session_id = candidate_id
                    session_data = session_entry[1]
            else:
                session_id = _SESSION_ID_PREFIX + secrets.token_urlsafe(32)
                session_data = {"orhex_session": session_id}

            if not legacy_session_unavailable:
                self.sessions[session_id] = (now + _SESSION_MAX_AGE, session_data)
                self.request_count += 1
                if self.request_count % 100 == 0:
                    self.sessions = {
                        key: value
                        for key, value in self.sessions.items()
                        if value[0] > now
                    }

        if legacy_session_unavailable:
            await JSONResponse(
                status_code=409,
                content={
                    "detail": (
                        "This legacy session cannot be restored after a server "
                        "restart. Its Walrus namespace must be migrated before "
                        "this session can continue."
                    )
                },
            )(scope, receive, send)
            return

        scope["session"] = session_data
        cookie = (
            f"{_SESSION_COOKIE_NAME}={session_id}; Max-Age={_SESSION_MAX_AGE}; "
            "Path=/; HttpOnly; SameSite=Lax"
        )
        if self.cookie_secure:
            cookie += "; Secure"

        async def send_with_session_cookie(message: Message) -> None:
            if message["type"] == "http.response.start":
                message = dict(message)
                message["headers"] = [
                    *message.get("headers", []),
                    (b"set-cookie", cookie.encode("latin-1")),
                ]
            await send(message)

        await self.app(scope, receive, send_with_session_cookie)


app.add_middleware(OpaqueSessionMiddleware, cookie_secure=_session_cookie_secure())


class RememberRequest(BaseModel):
    text: str = Field(min_length=3, max_length=8000)
    idempotency_key: UUID | None = None

    @field_validator("text")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Memory text must contain at least 3 non-whitespace characters.")
        return normalized


class RecallRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        normalized = value.strip()
        if len(normalized) < 3:
            raise ValueError("Recall query must contain at least 3 non-whitespace characters.")
        return normalized


def _remember_status(status: Any, namespace: str) -> dict[str, Any]:
    state = status.status
    blob_id = status.blob_id
    error = status.error
    if state == "confirmed" and (not isinstance(blob_id, str) or not blob_id):
        state = "reconciliation_required"
        error = "Walrus did not return a blob ID with its confirmation."
    return {
        "job_id": status.job_id,
        "status": state,
        "blob_id": blob_id,
        "namespace": namespace,
        "error": error,
    }


def _session_namespace(request: Request) -> str:
    session_id = request.session.get("orhex_session")
    if not isinstance(session_id, str):
        session_id = secrets.token_urlsafe(24)
        request.session["orhex_session"] = session_id
    owner_hash = hashlib.sha256(session_id.encode("utf-8")).hexdigest()[:20]
    return f"{MEMWAL_NAMESPACE[:107]}-{owner_hash}"


def _walrus_configuration_error() -> str | None:
    if not MEMWAL_PRIVATE_KEY or not MEMWAL_ACCOUNT_ID:
        return "Walrus Mainnet credentials are not configured."
    if not re.fullmatch(r"[0-9a-fA-F]{64}", MEMWAL_PRIVATE_KEY):
        return "Walrus delegate private key configuration is invalid."
    if not re.fullmatch(r"0x[0-9a-fA-F]{64}", MEMWAL_ACCOUNT_ID):
        return "Walrus account ID configuration is invalid."
    return None


def _walrus_client() -> Any:
    error = _walrus_configuration_error()
    if error:
        raise HTTPException(status_code=503, detail=error)
    try:
        return MemWal.create(
            key=MEMWAL_PRIVATE_KEY,
            account_id=MEMWAL_ACCOUNT_ID,
            server_url=MEMWAL_SERVER_URL,
            namespace=MEMWAL_NAMESPACE,
        )
    except (MemWalError, ValueError, TypeError) as exc:
        logger.exception("Could not initialize Walrus SDK client.")
        raise HTTPException(status_code=503, detail="Walrus SDK client initialization failed.") from exc


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "orhex-api"}


@app.get("/integrations/status", tags=["integrations"])
async def integration_status() -> dict[str, dict[str, Any]]:
    walrus: dict[str, Any] = {"network": "mainnet", "status": "unavailable"}
    if _walrus_configuration_error() is None:
        client = _walrus_client()
        try:
            health = await client.health()
            walrus.update(
                status="ready" if health.write_ready is True else "degraded",
                relayer_status=health.status,
                write_ready=health.write_ready,
            )
        except (MemWalError, TimeoutError, httpx.HTTPError) as exc:
            logger.warning("Walrus readiness check failed: %s", type(exc).__name__)
            walrus.update(status="unreachable", error=type(exc).__name__)
        finally:
            await client.close()

    tatum: dict[str, Any] = {"network": SUI_NETWORK, "status": "unavailable"}
    if TATUM_API_KEY:
        try:
            await _tatum_query(
                "query OrhexNetworkStatus { chainIdentifier checkpoints(last: 1) { nodes { sequenceNumber } } }",
                {},
            )
            tatum.update(status="ready", source="Tatum Sui GraphQL")
        except HTTPException as exc:
            logger.warning("Tatum Sui readiness check failed: %s", exc.status_code)
            tatum.update(status="unreachable", error=exc.status_code)
    return {"walrus": walrus, "tatum": tatum}


@app.post("/memory/remember", tags=["memory"])
async def remember(body: RememberRequest, request: Request) -> dict[str, Any]:
    client = _walrus_client()
    namespace = _session_namespace(request)
    operation_key = str(body.idempotency_key or uuid4())
    try:
        accepted = await client.remember(
            text=body.text.strip(),
            namespace=namespace,
            idempotency_key=operation_key,
        )
        job_id = getattr(accepted, "job_id", None)
        if not isinstance(job_id, str) or not job_id:
            raise HTTPException(status_code=502, detail="Walrus accepted no verifiable job ID.")
        jobs = request.session.get("orhex_jobs", [])
        if not isinstance(jobs, list):
            jobs = []
        if job_id not in jobs:
            jobs.append(job_id)
        request.session["orhex_jobs"] = jobs[-20:]
        try:
            status = await client.get_remember_status(job_id)
        except (MemWalError, TimeoutError, httpx.HTTPError) as exc:
            logger.warning(
                "Walrus accepted memory job but status check failed: %s",
                type(exc).__name__,
            )
            return {
                "job_id": job_id,
                "status": "pending",
                "blob_id": None,
                "namespace": namespace,
                "error": "Walrus accepted the write; confirmation is not yet available.",
            }
        return _remember_status(status, namespace)
    except HTTPException:
        raise
    except (MemWalError, TimeoutError, httpx.HTTPError) as exc:
        logger.exception("Walrus memory write could not be confirmed.")
        raise HTTPException(
            status_code=502,
            detail="Walrus memory write could not be confirmed. Check status before retrying.",
        ) from exc
    finally:
        await client.close()


@app.get("/memory/status/{job_id}", tags=["memory"])
async def remember_status(job_id: str, request: Request) -> dict[str, Any]:
    jobs = request.session.get("orhex_jobs", [])
    if not isinstance(jobs, list) or job_id not in jobs:
        raise HTTPException(status_code=404, detail="No memory operation found for this session.")
    client = _walrus_client()
    try:
        status = await client.get_remember_status(job_id)
        return _remember_status(status, status.namespace or _session_namespace(request))
    except (MemWalError, TimeoutError, httpx.HTTPError) as exc:
        logger.exception("Walrus memory write status could not be confirmed.")
        raise HTTPException(status_code=502, detail="Walrus write status could not be confirmed.") from exc
    finally:
        await client.close()


@app.post("/memory/recall", tags=["memory"])
async def recall(body: RecallRequest, request: Request) -> dict[str, Any]:
    client = _walrus_client()
    namespace = _session_namespace(request)
    try:
        result = await client.recall(
            RecallParams(query=body.query.strip(), limit=body.limit, namespace=namespace)
        )
        return {
            "namespace": namespace,
            "results": [
                {
                    "blob_id": item.blob_id,
                    "text": item.text,
                    "score": item.score,
                    "created_at": item.created_at,
                }
                for item in result.results
            ],
        }
    except (MemWalError, TimeoutError, httpx.HTTPError) as exc:
        logger.exception("Walrus memory recall failed.")
        raise HTTPException(status_code=502, detail="Walrus memory recall failed.") from exc
    finally:
        await client.close()


def _normalize_sui_address(address: str) -> str:
    payload = address[2:] if address[:2].lower() == "0x" else address
    if not re.fullmatch(r"[0-9a-fA-F]{1,64}", payload):
        raise HTTPException(status_code=422, detail="Provide a valid Sui address.")
    return f"0x{payload}"


async def _tatum_query(query: str, variables: dict[str, Any]) -> dict[str, Any]:
    if not TATUM_API_KEY:
        raise HTTPException(status_code=503, detail="Tatum API key is not configured.")
    chain = _SUI_MAINNET_CHAIN if SUI_NETWORK == "mainnet" else (
        _SUI_TESTNET_CHAIN if SUI_NETWORK == "testnet" else None
    )
    if chain is None:
        raise HTTPException(status_code=503, detail="Configured Sui network is unsupported.")
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            response = await client.post(
                f"{TATUM_SUI_RPC_URL}/graphql",
                json={"query": query, "variables": variables},
                headers={"Content-Type": "application/json", "x-api-key": TATUM_API_KEY},
            )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("Tatum Sui request failed: %s", type(exc).__name__)
        raise HTTPException(status_code=502, detail="Tatum Sui request failed.") from exc
    if not isinstance(payload, dict) or payload.get("errors") or not isinstance(payload.get("data"), dict):
        raise HTTPException(status_code=502, detail="Tatum returned an invalid Sui response.")
    if payload["data"].get("chainIdentifier") != chain:
        raise HTTPException(status_code=502, detail="Tatum Sui network identity did not match configuration.")
    return payload["data"]


@app.get("/sui/wallet/{address}", tags=["sui"])
async def sui_wallet(address: str) -> dict[str, Any]:
    address = _normalize_sui_address(address)
    data = await _tatum_query(
        """
        query OrhexWallet($address: SuiAddress!) {
          chainIdentifier
          address(address: $address) {
            balance(coinType: "0x2::sui::SUI") { totalBalance }
            transactions(last: 5, filter: { sentAddress: $address }) {
              nodes { digest effects { timestamp status } }
            }
          }
          checkpoints(last: 1) { nodes { sequenceNumber } }
        }
        """,
        {"address": address},
    )
    account = data.get("address")
    balance = account.get("balance") if isinstance(account, dict) else None
    raw_balance = balance.get("totalBalance") if isinstance(balance, dict) else None
    if (
        isinstance(raw_balance, bool)
        or not isinstance(raw_balance, (str, int))
        or not str(raw_balance).isascii()
        or not str(raw_balance).isdigit()
    ):
        raise HTTPException(status_code=502, detail="Tatum returned an invalid SUI balance.")
    checkpoints = data.get("checkpoints")
    nodes = checkpoints.get("nodes") if isinstance(checkpoints, dict) else None
    if not isinstance(nodes, list) or not nodes or not isinstance(nodes[-1], dict):
        raise HTTPException(status_code=502, detail="Tatum returned no latest Sui checkpoint.")
    try:
        raw_checkpoint = nodes[-1].get("sequenceNumber")
        if (
            isinstance(raw_checkpoint, bool)
            or not isinstance(raw_checkpoint, (str, int))
            or not str(raw_checkpoint).isascii()
            or not str(raw_checkpoint).isdigit()
        ):
            raise ValueError("Invalid checkpoint")
        checkpoint = int(raw_checkpoint)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="Tatum returned an invalid Sui checkpoint.") from exc
    if checkpoint < 0:
        raise HTTPException(status_code=502, detail="Tatum returned an invalid Sui checkpoint.")
    transactions = account.get("transactions") if isinstance(account, dict) else None
    nodes = transactions.get("nodes") if isinstance(transactions, dict) else None
    if not isinstance(nodes, list):
        raise HTTPException(status_code=502, detail="Tatum returned invalid Sui activity.")
    activity = []
    for item in nodes:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("digest"), str)
            or not item["digest"]
        ):
            raise HTTPException(status_code=502, detail="Tatum returned invalid Sui activity.")
        effects = item.get("effects")
        if effects is not None and not isinstance(effects, dict):
            raise HTTPException(status_code=502, detail="Tatum returned invalid Sui activity.")
        timestamp = effects.get("timestamp") if effects else None
        status = effects.get("status", "unknown") if effects else "unknown"
        if (timestamp is not None and not isinstance(timestamp, str)) or not isinstance(status, str):
            raise HTTPException(status_code=502, detail="Tatum returned invalid Sui activity.")
        activity.append({
            "digest": item["digest"],
            "timestamp": timestamp,
            "status": status,
        })
    return {
        "address": address,
        "network": SUI_NETWORK,
        "source": "Tatum Sui GraphQL",
        "balance_mist": str(raw_balance),
        "balance_sui": f"{Decimal(str(raw_balance)) / Decimal(1_000_000_000):.4f}",
        "latest_checkpoint": checkpoint,
        "activity": activity,
    }
