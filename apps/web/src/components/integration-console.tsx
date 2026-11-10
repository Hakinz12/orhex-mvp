"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { ArrowDownToLine, ArrowUpFromLine, Check, CircleAlert, LoaderCircle, RefreshCw, Search, Wallet } from "lucide-react";

type IntegrationStatus = {
  walrus: { status: string; network: string; write_ready?: boolean; relayer_status?: string };
  tatum: { status: string; network: string; source?: string };
};
type MemoryResult = {
  job_id?: string;
  status?: string;
  blob_id?: string | null;
  error?: string | null;
  results?: { blob_id: string; text: string; score?: number | null }[];
};
type WalletResult = {
  address: string;
  network: string;
  source: string;
  balance_sui: string;
  latest_checkpoint: number;
  activity: { digest: string; timestamp?: string | null; status: string }[];
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new Error("Cannot reach the ORHEX API. Start the API service and retry.");
  }
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new Error("ORHEX API returned an invalid response.");
  }
  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? body.detail
        : undefined;
    throw new Error(typeof detail === "string" ? detail : `ORHEX API returned HTTP ${response.status}.`);
  }
  return body as T;
}

function StateLabel({ status }: { status: string }) {
  const confirmed = status === "confirmed" || status === "ready";
  const failed = status === "failed" || status === "unreachable" || status === "unavailable";
  return (
    <span className={`integration-state${confirmed ? " confirmed" : failed ? " failed" : ""}`}>
      <span className="state-indicator" />{status.replaceAll("_", " ")}
    </span>
  );
}

export function IntegrationConsole() {
  const [services, setServices] = useState<IntegrationStatus | null>(null);
  const [statusError, setStatusError] = useState("");
  const [memoryText, setMemoryText] = useState("");
  const [idempotencyKey, setIdempotencyKey] = useState<string | null>(null);
  const [recallQuery, setRecallQuery] = useState("");
  const [memoryLoading, setMemoryLoading] = useState(false);
  const [memoryError, setMemoryError] = useState("");
  const [memoryResult, setMemoryResult] = useState<MemoryResult | null>(null);
  const [walletAddress, setWalletAddress] = useState("");
  const [walletLoading, setWalletLoading] = useState(false);
  const [walletError, setWalletError] = useState("");
  const [walletResult, setWalletResult] = useState<WalletResult | null>(null);

  const refreshStatus = useCallback(async () => {
    setStatusError("");
    try {
      setServices(await request<IntegrationStatus>("/integrations/status"));
    } catch (error) {
      setStatusError(error instanceof Error ? error.message : "Could not read integration status.");
      setServices(null);
    }
  }, []);

  useEffect(() => {
    void refreshStatus();
  }, [refreshStatus]);

  async function submitMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMemoryLoading(true);
    setMemoryError("");
    setMemoryResult(null);
    const operationKey = idempotencyKey ?? crypto.randomUUID();
    setIdempotencyKey(operationKey);
    try {
      const saved = await request<MemoryResult>("/memory/remember", {
        method: "POST",
        body: JSON.stringify({
          text: memoryText,
          idempotency_key: operationKey,
        }),
      });
      setMemoryResult(saved);
      setMemoryText("");
      setIdempotencyKey(null);
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : "Memory write failed.");
    } finally {
      setMemoryLoading(false);
    }
  }

  async function recallMemory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMemoryLoading(true);
    setMemoryError("");
    setMemoryResult(null);
    try {
      setMemoryResult(await request<MemoryResult>("/memory/recall", {
        method: "POST",
        body: JSON.stringify({ query: recallQuery, limit: 5 }),
      }));
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : "Memory retrieval failed.");
    } finally {
      setMemoryLoading(false);
    }
  }

  async function reconcile(jobId: string) {
    setMemoryLoading(true);
    setMemoryError("");
    try {
      setMemoryResult(await request<MemoryResult>(`/memory/status/${encodeURIComponent(jobId)}`));
    } catch (error) {
      setMemoryError(error instanceof Error ? error.message : "Could not verify the memory write.");
    } finally {
      setMemoryLoading(false);
    }
  }

  async function lookupWallet(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setWalletLoading(true);
    setWalletError("");
    setWalletResult(null);
    try {
      setWalletResult(await request<WalletResult>(`/sui/wallet/${encodeURIComponent(walletAddress.trim())}`));
    } catch (error) {
      setWalletError(error instanceof Error ? error.message : "Sui lookup failed.");
    } finally {
      setWalletLoading(false);
    }
  }

  return (
    <section className="live-console" aria-label="Live integration controls">
      <div className="console-heading">
        <div>
          <div className="eyebrow">LIVE PROVIDER CONTROLS</div>
          <h2>Bring your context online</h2>
          <p>These controls call real providers through the server. No demo data is used.</p>
        </div>
        <button className="console-refresh" type="button" onClick={() => void refreshStatus()} aria-label="Refresh integration status">
          <RefreshCw size={14} /> Check status
        </button>
      </div>
      <div className="provider-status-row">
        <span><strong>Walrus Mainnet</strong><StateLabel status={services?.walrus.status ?? "unknown"} /></span>
        <span><strong>Tatum · {services?.tatum.network ?? "Sui"}</strong><StateLabel status={services?.tatum.status ?? "unknown"} /></span>
        {statusError && <p className="inline-error" role="alert">{statusError}</p>}
      </div>
      <div className="console-grid">
        <article className="console-pane">
          <div className="console-title"><span className="console-icon walrus-console-icon"><ArrowUpFromLine size={16} /></span><span><strong>Save & recall memory</strong><small>Scoped to this browser session</small></span></div>
          <form onSubmit={submitMemory} className="console-form">
            <label htmlFor="memory-text">A memory to keep</label>
            <textarea id="memory-text" maxLength={8000} minLength={3} required value={memoryText} onChange={(event) => { setMemoryText(event.target.value); setIdempotencyKey(null); }} placeholder="For example: I prefer concise project updates with clear next steps." />
            <button type="submit" className="console-action" disabled={memoryLoading || !services?.walrus.write_ready}>
              {memoryLoading ? <LoaderCircle className="spinning" size={14} /> : <ArrowUpFromLine size={14} />}
              {memoryLoading ? "Contacting Walrus…" : "Save to Walrus"}
            </button>
            {services && !services.walrus.write_ready && <p className="data-source-note">Walrus is not write-ready. Configure valid server credentials and a healthy Mainnet relayer before saving.</p>}
          </form>
          <form onSubmit={recallMemory} className="console-form recall-form">
            <label htmlFor="recall-query">Recall something</label>
            <div className="inline-input"><input id="recall-query" minLength={3} required value={recallQuery} onChange={(event) => setRecallQuery(event.target.value)} placeholder="What should I remember?" /><button type="submit" aria-label="Recall memories" disabled={memoryLoading}><Search size={14} /></button></div>
          </form>
          {memoryError && <p className="inline-error" role="alert"><CircleAlert size={14} />{memoryError}</p>}
          {memoryResult && (
            <div className="provider-result" aria-live="polite">
              {memoryResult.results ? (
                <>
                  <strong><ArrowDownToLine size={14} /> Walrus returned {memoryResult.results.length} matching memories</strong>
                  {memoryResult.results.map((item) => <p key={item.blob_id}>{item.text}<small>Blob {item.blob_id}</small></p>)}
                </>
              ) : (
                <>
                  <strong><StateLabel status={memoryResult.status ?? "unknown"} /> {memoryResult.status === "confirmed" ? "Persistence confirmed by Walrus" : "Write submitted; persistence is not yet confirmed"}</strong>
                  {memoryResult.blob_id && <small className="blob-id">Blob ID · {memoryResult.blob_id}</small>}
                  {memoryResult.error && <small className="blob-id">{memoryResult.error}</small>}
                  {memoryResult.job_id && memoryResult.status !== "confirmed" && (
                    <button className="verify-action" type="button" disabled={memoryLoading} onClick={() => memoryResult.job_id && void reconcile(memoryResult.job_id)}>
                      Verify write status
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </article>
        <article className="console-pane">
          <div className="console-title"><span className="console-icon tatum-console-icon"><Wallet size={16} /></span><span><strong>Sui wallet lookup</strong><small>Public read-only network data</small></span></div>
          <form onSubmit={lookupWallet} className="console-form">
            <label htmlFor="sui-address">Sui address</label>
            <div className="inline-input"><input id="sui-address" required value={walletAddress} onChange={(event) => setWalletAddress(event.target.value)} placeholder="0x…" /><button type="submit" aria-label="Look up Sui wallet" disabled={walletLoading || !services?.tatum.status || services.tatum.status !== "ready"}>{walletLoading ? <LoaderCircle className="spinning" size={14} /> : <Search size={14} />}</button></div>
          </form>
          {walletError && <p className="inline-error" role="alert"><CircleAlert size={14} />{walletError}</p>}
          {walletResult && (
            <div className="provider-result wallet-result" aria-live="polite">
              <strong><Check size={14} /> Live result · {walletResult.source}</strong>
              <div className="wallet-stats"><span><small>SUI BALANCE</small><b>{walletResult.balance_sui} SUI</b></span><span><small>LATEST CHECKPOINT</small><b>{walletResult.latest_checkpoint.toLocaleString()}</b></span></div>
              <div className="activity-list">
                {walletResult.activity.length ? walletResult.activity.map((item) => <p key={item.digest}><span>{item.status}</span><code>{item.digest.slice(0, 12)}…{item.digest.slice(-6)}</code></p>) : <p>No recent sent activity returned.</p>}
              </div>
            </div>
          )}
          <p className="data-source-note">Addresses and balances are public on-chain information. ORHEX never requests signing keys or transactions.</p>
        </article>
      </div>
    </section>
  );
}
