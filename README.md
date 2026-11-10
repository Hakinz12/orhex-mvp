# ORHEX MVP

ORHEX is a personal intelligence workspace built around persistent context and read-only Sui data. This independent MVP keeps the ORHEX orbital identity and separates the web app from its API so provider credentials remain server-side.

## Current scope

The dashboard, session-scoped Walrus save/status/recall controls, and read-only Tatum Sui lookup are implemented. They call real providers only when valid server-side credentials are configured. This environment has not verified either provider, and there is no AI conversation feature yet; those must not be presented as complete.

## Requirements

- Node.js 20 or newer and npm
- Python 3.11 or newer

## Run locally

1. Copy `.env.example` to `.env` at the project root and fill only the provider credentials you have. The example contains names and descriptions but no sample secrets. The API reads Walrus and Tatum credentials from this server-side file and creates anonymous sessions automatically. Copy `apps\web\.env.example` to `apps\web\.env.local` and set `ORHEX_API_BASE_URL=http://127.0.0.1:8000` for local development.

   Walrus uses its Mainnet relayer by default (`https://relayer.memory.walrus.xyz`); provide `MEMWAL_ACCOUNT_ID` and `MEMWAL_PRIVATE_KEY`. Tatum defaults to `https://sui-mainnet.gateway.tatum.io`; provide `TATUM_API_KEY`. The API refuses to report either provider ready unless it completes a live readiness request.
2. Start the frontend:

   ```powershell
   cd apps\web
   npm install
   npm run dev
   ```

   Open `http://localhost:3000`.

3. In a separate terminal, start the API:

   ```powershell
   cd services\api
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   py -m pip install -r requirements.txt
   py -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```

   The API health check is at `http://127.0.0.1:8000/health`.

## Tests and checks

From `apps\web`:

```powershell
npm run lint
npm run build
```

From `services\api`:

```powershell
py -m pytest
```

## Deployment preparation

Example free-tier deployment (availability and limits can change):

1. Create a Render Web Service from this repository, with root directory `services/api`, build command `pip install -r requirements.txt`, and start command `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Set `APP_ENV=production`, explicit `CORS_ORIGINS`, and Walrus/Tatum credentials in Render's environment settings. Production sessions use `Secure` cookies automatically; no session secret is required.
2. Create a Vercel project from this repository with root directory `apps/web`. Set `ORHEX_API_BASE_URL` to the Render HTTPS base URL in Vercel's build/runtime environment so Next.js proxies same-origin `/api/*` requests and browser session cookies remain first-party.
3. Configure the Render CORS origin to the exact Vercel HTTPS origin, redeploy, and verify `/api/integrations/status` from the deployed site before attempting provider operations.

Session cookies contain a cryptographically random opaque bearer ID and are `HttpOnly` and `SameSite=Lax`; unlike signed cookies, they have no signature or integrity protection. Anyone who steals an ID can impersonate that session, and the server cannot revoke or validate stateless IDs. New versioned session IDs remain stable across process restarts without a database, and their Walrus namespace uses the existing session-ID hash derivation. Per-session Walrus job-status tracking is still held in API process memory, so a restart can invalidate status checks for pending jobs.

Legacy unversioned session IDs depended on an in-memory mapping to a separate Walrus namespace seed. If that mapping is still present in the running process, it remains usable; after a restart it cannot be reconstructed from the cookie. The API returns `409` for such an unmapped legacy cookie rather than silently switching the user to a new namespace. Preserving those legacy sessions requires exporting and migrating their cookie-to-namespace mappings while the old process is still available; this transition cannot recover mappings already lost to a restart. Never put provider credentials in `NEXT_PUBLIC_*` variables or browser code. Free instances may sleep and introduce cold-start delays; wait for explicit provider confirmation before the judge demo.

## Judge demo flow

1. Start the API and web app, then open the dashboard.
2. Check that Walrus Mainnet and Tatum Sui show live readiness; if credentials or providers are unavailable, the UI says so.
3. Enter a real, user-approved personal fact and choose **Save to Walrus**. A pending response is not described as persisted; use **Verify write status** until Walrus returns a confirmed status and blob ID.
4. Search for that fact using **Recall something** and show the actual result returned from Walrus.
5. Enter a public Sui address and show the SUI balance, checkpoint, and activity returned by Tatum.
6. Capture evidence only from confirmed provider responses. The MVP does not ship seeded, fabricated, or mocked memory records.

## Project story

People repeat the same context to every new assistant. ORHEX explores a more continuous alternative: a personal AI workspace where a user can intentionally save context to Walrus, recall it later, and inspect live public Sui signals through Tatum. The demo favors evidence over illusion: an accepted write remains pending until Walrus confirms it, provider failures are visible, and blockchain access is read-only. ORHEX keeps the user in control of what becomes part of the record.

The concise submission story is also available in [`docs/project-story.md`](docs/project-story.md).

## Remaining for a submission

- Configure Walrus Mainnet and Tatum credentials in the MVP only.
- Verify ten real Walrus writes reach `confirmed`, and preserve their returned blob IDs as evidence.
- Verify a live Tatum Sui response with a valid public address.
- Add the AI conversation workflow only if time remains after those demonstrations pass.
