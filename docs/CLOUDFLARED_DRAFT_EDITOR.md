# Cloudflare Tunnel for Draft Editor + calendar `.ics`

Use this when you want `CALENDAR_PUBLIC_BASE_URL` to be a real `https://` host (e.g. links inside subscribed calendars on your phone).

## Multiple tunnels (Draft Editor + DeerFlow Gateway)

One `cloudflared` process = one public URL. To expose **two** locals at once:

```bash
chmod +x scripts/cloudflared-tunnels.sh scripts/cloudflared-print-urls.sh
./scripts/cloudflared-tunnels.sh
```

Default maps:

| Label | Local |
|-------|--------|
| `draft-editor` | `http://127.0.0.1:8081` |
| `deerflow-gateway` | `http://127.0.0.1:8001` |

Logs: `.cloudflared-logs/<label>.log`. After a few seconds:

```bash
./scripts/cloudflared-print-urls.sh
```

Or: `grep trycloudflare .cloudflared-logs/draft-editor.log`

Override ports / services:

```bash
CLOUDFLARED_TUNNELS="8081:draft-editor 3000:ui" ./scripts/cloudflared-tunnels.sh
```

**Draft Editor only** (backward compatible):

```bash
./scripts/cloudflared-draft-editor.sh
```

## Quick tunnel vs your own DNS (stability)

| Mode | URL | Typical stability |
|------|-----|-------------------|
| **Quick tunnel** (`cloudflared tunnel --url …` / trycloudflare) | Random `*.trycloudflare.com` each run | Can reconnect often; control stream errors are common on some networks/VPNs. Fine for dev. |
| **Named tunnel + DNS** | `https://draft.yourdomain.com` (you choose) | **Much more stable** — same hostname, traffic pinned to your tunnel; you add a **CNAME** (or Cloudflare routes it automatically if the zone is on CF). |

So: quick tunnels are not “broken,” but they **can** stop or churn more than a named tunnel. For anything you rely on daily (calendar feed, Shiftshapr webhooks), use a **named tunnel** on a hostname you control.

## Quick Tunnel (free, new URL each time)

1. Start local services (Draft Editor on **8081**, and if using multi-script, Gateway on **8001**).
2. Run `./scripts/cloudflared-tunnels.sh` or `./scripts/cloudflared-draft-editor.sh`.
3. Copy the `https://….trycloudflare.com` URL(s) from logs into `.env`:

   ```env
   CALENDAR_PUBLIC_BASE_URL=https://….trycloudflare.com
   ```

4. Restart Draft Editor so it picks up the env.

**Note:** Quick tunnels change hostname every run. Re-subscribe or update `.env` when you restart the tunnel.

## HTTP 502 Bad Gateway (browser shows 502 on your tunnel URL)

A **502** from `*.trycloudflare.com` (or your named tunnel hostname) usually means **Cloudflare could not reach your local app** — not a Flask bug.

1. **Confirm the app is running** on the port `cloudflared` forwards to (default **8081** for Draft Editor):  
   `curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8081/`  
   You want `200` or `401` (basic auth), not `Connection refused`.
2. **Open the same path locally** — e.g. Bride dashboard:  
   [http://127.0.0.1:8081/bride_of_charlie/](http://127.0.0.1:8081/bride_of_charlie/)  
   If local works but the tunnel 502s, restart **one** `cloudflared` process (`pkill cloudflared` then your tunnel script).
3. **Wrong port in tunnel** — if Flask uses another port, update the tunnel config or set `DRAFT_EDITOR_LOCAL_URL` in `.env` (see Draft Editor env example) so in-app “open locally” links match reality.

The Bride hub dashboard shows a **yellow “open localhost” banner** only when the `Host` looks like a **quick tunnel** (`trycloudflare.com`), or when you set `DRAFT_EDITOR_SHOW_LOCAL_FALLBACK_BANNER=1`. **Stable domains** (e.g. `*.metawebbook.com`) stay clean — use `DRAFT_EDITOR_LOCAL_FALLBACK_BANNER_HOST_SUFFIXES` (comma-separated) if you want the tip on other ephemeral hosts, or `DRAFT_EDITOR_HIDE_LOCAL_FALLBACK_BANNER=1` to suppress it everywhere.

---

## Tunnel errors: `control stream encountered a failure` / `context canceled`

Usually **not** your app — the **Cloudflare ↔ cloudflared** QUIC/control channel is flapping. Try in order:

1. **Stop every cloudflared** — `pkill cloudflared` — then start **one** tunnel only:  
   `CLOUDFLARED_TUNNELS="8081:draft-editor" ./scripts/cloudflared-tunnels.sh`
2. **Upgrade** — `brew upgrade cloudflare/cloudflare/cloudflared`
3. **Force HTTP/2** (bypasses some QUIC issues on certain networks):  
   `export TUNNEL_TRANSPORT_PROTOCOL=http2`  
   then run the tunnel script again.
4. **VPN / captive Wi‑Fi** — disable VPN or try another network.
5. **Sleep / network change** — restart tunnel after wake-from-sleep.

If two quick tunnels run at once and both flake, use **one** tunnel for Draft Editor only until stable, or set up a **named tunnel** in Cloudflare (more reliable than trycloudflare for long sessions).

## Named tunnel (your DNS — recommended for reliability)

You still use **cloudflared** as the connector; the difference is Cloudflare assigns a **persistent tunnel ID** and you map **your domain** to it (DNS is managed in the Cloudflare dashboard if your domain is on Cloudflare).

1. [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) → **Networks** → **Connectors** → create a **tunnel**.
2. Name it (e.g. `home-mac`), install/run the **connector** command on your Mac (same `cloudflared` binary).
3. **Public hostnames** (same tunnel, multiple rows): e.g. `draft` → `http://127.0.0.1:8081`, `deerflow` → `http://127.0.0.1:8001`. **Do not create two tunnels** on one Mac just for two subdomains — one connector handles both.
4. Cloudflare creates the **DNS record** for you (proxied). No manual CNAME needed unless you use a non-CF DNS provider (then CNAME to the tunnel target Cloudflare shows).

Set `CALENDAR_PUBLIC_BASE_URL=https://draft.yourdomain.com` (no trailing slash).

### macOS: `cloudflared service is already installed`

`sudo cloudflared service install <token>` registers **one** LaunchDaemon (`/Library/LaunchDaemons/com.cloudflare.cloudflared.plist`). A **second** `service install` with another token fails by design.

- **Right approach:** keep that single service; add **all** public hostnames under **that** tunnel in the dashboard.
- **To switch tunnels:** `sudo cloudflared service uninstall`, then `sudo cloudflared service install <new-token>`.

**Cost:** Tunnels are included on free Cloudflare accounts; you pay only for your domain registration if applicable.

## Verify

- Open `https://YOUR_HOST/` in a browser — Draft Editor login.
- Calendar subscribe URL (with token):  
  `https://YOUR_HOST/api/calendar/feed.ics?token=YOUR_CALENDAR_EMBED_TOKEN`

## Bride hub (DeerFlow UI + Draft Editor API)

When DeerFlow’s Next.js app is exposed (e.g. `deerflow.metawebbook.com` → port **3000**), you can use **`/bride-of-charlie`** as a read-only hub that proxies to Draft Editor. The Next.js route **`/api/draft-editor-hub/...`** forwards **GET**, **POST**, **PUT**, and **HEAD** to Draft Editor (HEAD is useful for probes).

**Draft Editor** (same host you already tunnel for port **8081**) gains:

- `GET /api/bride/hub/index` — cached episode index + `file_id` map  
- `GET /api/bride/hub/entity-detail?id=C-1000` — one node / claim / artifact from inscription JSON + YouTube `watch` / `embed` URLs; optional `&episode=N` to narrow search  
- `GET /api/bride/hub/health` — bride dir exists, fingerprint, index cache age (no full rebuild)  
- `GET /api/bride/hub/neo4j` — read-only graph stats (same Cypher as `neo4j_validate.py`); **`?validate=1`** adds integrity check counts + sample rows. Needs **`neo4j`** Python package + **`NEO4J_*`** env and a running database.  
- `POST /api/bride/hub/activate` — body `youtube_url`; optional **`allow_duplicate: true`** skips **409** and appends another line anyway. Async fetch + corrected transcripts.  
- `GET /api/bride/hub/episode/<n>/transcript-diff` — unified diff raw vs `transcripts_corrected/` (JSON). Append **`?format=text`** for `text/plain` download.  
- `GET /bride_of_charlie/<file_id>` — in-browser text/json editor  

**DeerFlow frontend env** (see `framework/deer-flow/frontend/src/env.js`):

| Variable | Purpose |
|----------|---------|
| `DRAFT_EDITOR_HUB_URL` | Draft Editor origin for server-side proxy, e.g. `http://127.0.0.1:8081` |
| `DRAFT_EDITOR_HUB_USER` | Basic auth user (default `draft`) |
| `DRAFT_EDITOR_HUB_PASSWORD` | Same secret as `DRAFT_EDITOR_PASSWORD` |
| `NEXT_PUBLIC_DRAFT_EDITOR_FILE_BASE` | Public `https://draft-editor…` base for “open in editor” links |

Tunnel example: map **`deerflow`** → `http://127.0.0.1:3000` and **`draft`** → `http://127.0.0.1:8081` on one named tunnel.

UI routes on DeerFlow: **`/bride-of-charlie`** (episodes), **`/bride-of-charlie/episode/N`**, **`/bride-of-charlie/graph`** (Neo4j), **`/bride-of-charlie/nodes`**, **`/bride-of-charlie/claims`**, **`/bride-of-charlie/artifacts`**, **`/bride-of-charlie/diff?episode=N`**.
