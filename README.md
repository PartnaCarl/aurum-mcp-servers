# AURUM FBA MCP Servers

3 MCP servers for Amazon FBA sellers — built from a live wholesale FBA operation using 2026-accurate fee tables.

## Servers

### FBA Fee Calculator 2026
Accurate Amazon FBA fulfillment fees with 2026 rate tables including the April 3.5% surcharge.

**Tools:** `get_fba_fee`, `calculate_referral_fee`, `calculate_prep_cost`, `calculate_total_fees`

### Brand Compliance Checker
Check any brand for Amazon gating status and IP risk before buying wholesale inventory.

**Tools:** `check_brand`, `check_brands_batch`

**Status values:** `GATED` · `IP_RISKY` · `COMMINGLING_RISK` · `CLEAR`

### FBA SKU Scorer
T1/T2/T3 decision engine — BUY / PAPER TRADE / SKIP with full margin breakdown.

**Tools:** `score_sku`, `score_skus_batch`

**Tier thresholds:** T1 (BUY) >= 0.8 · T2 (PAPER TRADE) >= 0.4 · T3 (SKIP) < 0.4

The scorer includes: 2026 FBA fees, referral fees, AMSCO prep costs, inbound placement fees, return rate by category, LIVE fee risk, slow-mover surcharge, and seller competition weighting.

## Usage

Each server runs as a standalone MCP server via FastMCP.

```bash
pip install fastmcp
fastmcp run fba_fee_calculator_server.py
fastmcp run brand_compliance_server.py
fastmcp run sku_scorer_server.py
```

## Requirements

- Python 3.10+
- `fastmcp>=0.4.0`

## Fee Tables

Current as of 2026-01-15. Includes the April 2026 3.5% FBA surcharge.

| Size Tier | Weight | Fee |
|-----------|--------|-----|
| Small Standard | <= 4oz | $3.06 |
| Small Standard | <= 16oz | $3.33 |
| Large Standard | <= 2lb | $3.56 |
| Large Standard | <= 7lb | $6.60 |
| Large Bulky | base (2lb) | $9.61 |
| Large Bulky | per lb over 2lb | +$0.38 |

## Built by

Partna Company LLC — Carl Clendenin
