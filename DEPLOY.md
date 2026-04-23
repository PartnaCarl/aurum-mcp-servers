# AURUM Deployment Guide

Three MCP servers, three paid tiers ($9 / $15 / $19 per month), one landing page.

This is the shipping checklist. Work top-to-bottom.

---

## What's in this repo

| File | Purpose |
|---|---|
| `fba_fee_calculator_server.py` | 2026 FBA Fee Calculator — $9/mo tier |
| `brand_compliance_server.py` | Brand Compliance Checker (715+ brands) — $15/mo tier |
| `sku_scorer_server.py` | T1/T2/T3 SKU Scorer — $19/mo tier |
| `landing.html` | Public landing page with 3 pricing cards |
| `tests/` | pytest suite — 52 tests, all green |
| `requirements.txt` | `fastmcp>=2.10,<3`, `uvicorn>=0.30.0` |
| `runtime.txt` | `python-3.11.9` |
| `render.yaml` | Render.com web-service config for all 3 servers |
| `mcpize.*.json` | Per-server MCPize entry points |

---

## 1. Test locally before deploying

### Install dependencies

```bash
cd /Users/carl/Desktop/aurum-mcp-server
pip install -r requirements.txt
pip install pytest    # test-only dep
```

### Run the test suite

```bash
python -m pytest tests/ -v
```

Expected: **52 passed**. If anything fails, fix it before deploying — do not ship red tests.

### Run a server locally (HTTP transport)

Each server starts an HTTP MCP endpoint on `$PORT` (default 8000):

```bash
# Fee calculator on port 8001
PORT=8001 python fba_fee_calculator_server.py

# Brand compliance on port 8002
PORT=8002 python brand_compliance_server.py

# SKU scorer on port 8003
PORT=8003 python sku_scorer_server.py
```

### Test a running server with fastmcp

```bash
# In a separate terminal
fastmcp run http://localhost:8001
```

You should see the 4 tools exposed: `get_fba_fee`, `calculate_referral_fee`, `calculate_prep_cost`, `calculate_total_fees`.

---

## 2. Deploy the MCP servers

### Option A — Render.com (recommended)

`render.yaml` already declares all three services. Each one gets its own URL.

1. Push the repo to GitHub (see "Git push" section below).
2. Sign into Render.com → New → Blueprint → point at the repo.
3. Render reads `render.yaml` and spins up three web services:
   - `aurum-fba-fee-calculator`
   - `aurum-brand-compliance`
   - `aurum-sku-scorer`
4. Each ships at its own URL like `https://aurum-fba-fee-calculator.onrender.com`.
5. **Environment variables:** none required. `PORT` is injected by Render automatically.

### Option B — Any platform that reads `requirements.txt` + `runtime.txt`

Railway, Fly.io, Heroku, Replit — same pattern. Set `startCommand` to the server file you want.

### Option C — MCPize (https://mcpize.com)

There's one `mcpize.json` per server in the repo:
- `mcpize.fba.json` → `fba_fee_calculator_server.py`
- `mcpize.brand.json` → `brand_compliance_server.py`
- `mcpize.sku.json` → `sku_scorer_server.py`

MCPize reads the `entry_point` field. Deploy each one as a separate MCPize app so Carl can gate them per Stripe product.

---

## 3. Deploy the landing page

### Option A — Netlify (recommended for the landing)

```bash
# From repo root
netlify deploy --prod --dir . --site aurum-landing
```

Build settings:
- **Build command:** _none_ (static HTML)
- **Publish directory:** `.` (repo root)
- **Functions directory:** _none_

Set a custom domain after deploy (see step 5).

### Option B — Netlify drop-in

Drag `landing.html` into https://app.netlify.com/drop — done in 30 seconds, but no custom domain unless upgraded.

### Option C — Same Render repo as static asset

Add a second Render service of type `static` pointing at the repo root — `landing.html` becomes the index. Faster if Render is already hosting the servers.

---

## 4. Stripe wiring — **this is Carl's manual step**

Inside `landing.html`, three anchors have placeholder `href`s that must be replaced:

```html
<a href="#REPLACE_WITH_STRIPE_LINK_FEE_CALCULATOR" ...>
<a href="#REPLACE_WITH_STRIPE_LINK_BRAND_COMPLIANCE" ...>
<a href="#REPLACE_WITH_STRIPE_LINK_SKU_SCORER" ...>
```

### Step-by-step

1. Log into Stripe → Products → **+ Create product** three times:
   - **AURUM Fee Calculator** — $9.00 / month recurring
   - **AURUM Brand Compliance** — $15.00 / month recurring
   - **AURUM SKU Scorer** — $19.00 / month recurring
2. For each, click **Create payment link**. Enable "Quantity: 1 only", disable promo codes unless you want them.
3. Copy each Payment Link URL.
4. In `landing.html`, replace the three `#REPLACE_WITH_STRIPE_LINK_*` strings with the real URLs.
5. Commit and redeploy.

### Post-purchase fulfillment

Stripe Payment Links can be configured to redirect to a success URL. Send buyers to a page (or a simple `thank-you.html`) that delivers:
- The MCP server URL for their tier
- The MCPize connection instructions
- Carl's support email

Manual option until you build the delivery automation: wire the success URL to an email form, and mail the MCP endpoint manually for the first 30 days while volume is low. After that, use Stripe webhooks + a delivery Lambda.

---

## 5. Domain (also Carl's manual step)

- Buy `aurumfba.com` or `getaurum.com` (or whatever lands).
- In Netlify, add as custom domain on the landing site.
- The MCP server URLs can stay at `*.onrender.com` at launch — they're technical endpoints, not customer-facing pages.

---

## 6. Git push

This branch is `feature/autopilot-cleanup`.

```bash
git push -u origin feature/autopilot-cleanup
```

Then open a PR against `main` on GitHub, review, merge. The master repo is at
https://github.com/PartnaCarl/aurum-mcp-servers.

There are also two standalone repos (one per paid product) that Carl may be deploying independently:
- `/Users/carl/Desktop/aurum-sku-scorer/`
- `/Users/carl/Desktop/aurum-brand-compliance/`

The autopilot also synced updated files into those repos — commit and push each separately.

---

## 7. Checklist Carl must do manually

- [ ] Push `feature/autopilot-cleanup` branch to GitHub
- [ ] Merge PR to main (if using the feature-branch workflow)
- [ ] Sign into Render and provision from `render.yaml`
- [ ] Create 3 Stripe products + payment links ($9, $15, $19)
- [ ] Replace the 3 `#REPLACE_WITH_STRIPE_LINK_*` placeholders in `landing.html`
- [ ] Deploy `landing.html` to Netlify
- [ ] Buy domain + point DNS at Netlify
- [ ] Decide on fulfillment flow (manual email for first 30 days, then automate)
- [ ] Test each MCP server from Claude Desktop before charging anyone

---

## Troubleshooting

**"fastmcp not found"** — `pip install -r requirements.txt` in the right virtualenv.

**"Cannot import brand_compliance_server"** — The tests stub `fastmcp` in `tests/conftest.py`. If you're running server code standalone without fastmcp installed, that's the failure mode. Install the dep.

**Tests pass locally, fail in CI** — Likely pytest version. Pin it in `requirements.txt` if you add CI: `pytest>=8.0`.

**Render free tier spins down** — Servers sleep after 15 min idle. First request after sleep takes 20–30 seconds. Upgrade to paid (~$7/mo per service) once you have >10 paying customers.
