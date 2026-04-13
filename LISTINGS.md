# AURUM MCP Server Listings
Paste-ready copy for MCPize and Apify. Do not publish this file publicly.

---

## SERVER 1 — FBA Fee Calculator 2026

**Name:** FBA Fee Calculator 2026
**Tagline:** Accurate Amazon FBA fulfillment fees with 2026 rate tables

**Description (MCPize/Apify):**
Calculate exact Amazon FBA fulfillment fees using 2026 rate tables — including the
April 2026 3.5% surcharge. Works for standard, large standard, and oversize items.

Tools included:
- get_fba_fee — FBA fulfillment fee by weight and size tier
- calculate_referral_fee — Amazon referral fee by category
- calculate_prep_cost — AMSCO 3PL prep cost estimate (standard and oversize)
- calculate_total_fees — All-in fee breakdown: FBA + referral + prep + inbound placement

Built for FBA sellers and developers who need accurate 2026 cost modeling.
Fee tables are current as of 2026-01-15 and include the April surcharge.

**MCPize price:** $9/month
**Apify price:** $0.01/call

**Tags:** amazon, fba, ecommerce, fees, wholesale

---

## SERVER 2 — Brand Compliance Checker

**Name:** Brand Compliance Checker — Amazon FBA
**Tagline:** Check any brand for Amazon gating and IP risk before buying inventory

**Description (MCPize/Apify):**
Instantly check whether a brand is gated, IP-risky, or safe to sell on Amazon
before purchasing wholesale inventory. Prevents account suspensions and IP complaints.

Tools included:
- check_brand — Single brand lookup. Returns GATED / IP_RISKY / COMMINGLING_RISK / CLEAR
  with risk level and a specific recommendation for each status.
- check_brands_batch — Check an entire wholesale price list at once. Returns a summary
  (gated count, IP risky count, clear count) plus per-brand results sorted by risk.

Status meanings:
- GATED: Amazon requires approval. Do not source without applying first.
- IP_RISKY: High IP complaint history. Suspension risk even if ungated.
- COMMINGLING_RISK: Not gated, but counterfeit prevalence is high — use FNSKU labels only.
- CLEAR: No known issues. Normal due diligence applies.

Built from Amazon seller community data, SP-API gating records, and IP complaint history.

**MCPize price:** $15/month
**Apify price:** $0.02/call

**Tags:** amazon, fba, brand-gating, ip-risk, wholesale, compliance

---

## SERVER 3 — FBA SKU Scorer

**Name:** FBA SKU Scorer — T1/T2/T3 Decision Engine
**Tagline:** BUY / PAPER TRADE / SKIP decisions with full 2026 margin breakdown

**Description (MCPize/Apify):**
Score any Amazon FBA product using the T1/T2/T3 decision engine. Input a buy price
and product details, get a BUY / PAPER TRADE / SKIP decision with a complete margin
breakdown including all 2026 fees.

Tools included:
- score_sku — Score a single product. Returns tier, decision, PVS score, net margin,
  full fee breakdown, and risk flags (LIVE fee risk, slow-mover surcharge, high competition).
- score_skus_batch — Score multiple products at once, sorted T1 first.

What's included in the cost model:
- 2026 FBA fulfillment fees (including April surcharge)
- Amazon referral fee by category
- AMSCO prep cost (standard + oversize, label, inbound shipping)
- Inbound placement fee ($0.25 standard, $2.41 large bulky)
- Return rate by category (Electronics 15%, Pet 6%, Apparel 25%, etc.)
- LIVE fee risk (low-inventory surcharge trigger)
- Slow-mover surcharge (26-week storage)
- Seller competition weight (1–3 sellers = 1.0x, 11+ = 0.15x)

Tier thresholds:
- T1 (BUY): PVS score >= 0.8
- T2 (PAPER TRADE): PVS score >= 0.4
- T3 (SKIP): PVS score < 0.4 or margin < 10%

**MCPize price:** $19/month
**Apify price:** $0.05/call

**Tags:** amazon, fba, product-research, wholesale, sourcing, margin-calculator

---

## GitHub Repo Description
3 MCP servers for Amazon FBA sellers — accurate 2026 fee calculator, brand compliance
checker, and T1/T2/T3 SKU scoring engine. Built from a live wholesale FBA operation.
