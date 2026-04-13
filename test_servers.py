"""
test_servers.py — Validate core logic of all 3 AURUM MCP servers
without requiring FastMCP to be installed.

Run: python3 test_servers.py
"""

import sys

PASS = 0
FAIL = 0

def check(label, condition, detail=""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {label}")
        PASS += 1
    else:
        print(f"  FAIL  {label} {detail}")
        FAIL += 1

# ===========================================================================
# Inline the logic (no FastMCP import needed)
# ===========================================================================

# --- FBA Fee Calculator ---

FBA_FEES_2026 = {
    "small_standard_4oz": 3.06, "small_standard_8oz": 3.15,
    "small_standard_12oz": 3.24, "small_standard_16oz": 3.33,
    "large_standard_2lb": 3.56, "large_standard_3lb": 4.28,
    "large_standard_4lb": 5.09, "large_standard_5lb": 5.48,
    "large_standard_6lb": 6.32, "large_standard_7lb": 6.60,
    "large_bulky_base": 9.61, "large_bulky_per_lb": 0.38,
}
INBOUND_PLACEMENT_FEES = {"small_standard": 0.20, "standard_size": 0.25, "large_bulky": 2.41}
REFERRAL_RATES = {"Electronics": 0.08, "Grocery & Gourmet Food": 0.08, "Apparel": 0.17}
DEFAULT_REFERRAL_RATE = 0.15
PREP_BASE = {"standard": 1.75, "oversize": 3.50}
PREP_LABEL = 0.20
PREP_INBOUND_PER_LB = 0.45

def get_fba_fee(weight_oz, size_tier="standard_size"):
    if size_tier == "large_bulky":
        weight_lb = weight_oz / 16
        return FBA_FEES_2026["large_bulky_base"] + max(0, weight_lb - 2) * FBA_FEES_2026["large_bulky_per_lb"]
    if weight_oz <= 4:   return FBA_FEES_2026["small_standard_4oz"]
    if weight_oz <= 8:   return FBA_FEES_2026["small_standard_8oz"]
    if weight_oz <= 12:  return FBA_FEES_2026["small_standard_12oz"]
    if weight_oz <= 16:  return FBA_FEES_2026["small_standard_16oz"]
    if weight_oz <= 32:  return FBA_FEES_2026["large_standard_2lb"]
    if weight_oz <= 48:  return FBA_FEES_2026["large_standard_3lb"]
    if weight_oz <= 64:  return FBA_FEES_2026["large_standard_4lb"]
    if weight_oz <= 80:  return FBA_FEES_2026["large_standard_5lb"]
    if weight_oz <= 96:  return FBA_FEES_2026["large_standard_6lb"]
    return FBA_FEES_2026["large_standard_7lb"]

# --- Brand Compliance ---

GATED_BRANDS = {"nike", "apple", "disney", "sony", "lego", "hasbro", "mattel", "dyson",
                "shark", "irobot", "samsung", "bose", "beats", "adidas", "ugg"}
IP_RISKY_BRANDS = {"apple", "dyson", "shark", "irobot", "lego", "disney", "nike", "adidas",
                   "ugg", "gucci", "louis vuitton", "coach", "beats", "bose", "vitamix",
                   "yeti", "hydroflask"}
COMMINGLING_RISK_BRANDS = {"nike", "ugg", "north face", "gucci", "rayban", "beats",
                            "vitamix", "yeti", "hydroflask", "owala", "stanley", "lululemon"}

def check_brand(brand_name):
    b = brand_name.strip().lower()
    if b in IP_RISKY_BRANDS:
        return {"status": "IP_RISKY", "risk_level": "HIGH", "is_gated": b in GATED_BRANDS}
    if b in GATED_BRANDS:
        return {"status": "GATED", "risk_level": "MEDIUM", "is_gated": True}
    if b in COMMINGLING_RISK_BRANDS:
        return {"status": "COMMINGLING_RISK", "risk_level": "LOW"}
    return {"status": "CLEAR", "risk_level": "NONE"}

# --- SKU Scorer ---

MARGIN_BUFFER_PCT = 0.15
CATEGORY_RETURN_RATES = {
    "Pet Supplies": 0.06, "Home & Kitchen": 0.10, "Electronics": 0.15,
    "Apparel": 0.25, "Health & Household": 0.08,
}
DEFAULT_RETURN_RATE = 0.08

def _seller_weight(n):
    if n <= 3: return 1.00
    if n <= 6: return 0.75
    if n <= 10: return 0.50
    return 0.15

def score_sku(buy_price, sell_price, weight_oz=16, size_tier="standard_size",
              category="Home & Kitchen", seller_count=5, estimated_monthly_units=50,
              days_to_sell_through=30, weight_lbs=1.0):
    fba = get_fba_fee(weight_oz, size_tier)
    referral = sell_price * REFERRAL_RATES.get(category, DEFAULT_REFERRAL_RATE)
    prep = PREP_BASE["standard"] + PREP_LABEL + (PREP_INBOUND_PER_LB * weight_lbs)
    placement = INBOUND_PLACEMENT_FEES.get(size_tier, 0.25)
    total_costs = buy_price + fba + prep + placement + referral
    net_margin = sell_price - total_costs
    net_margin_pct = net_margin / sell_price if sell_price > 0 else 0
    return_rate = CATEGORY_RETURN_RATES.get(category, DEFAULT_RETURN_RATE)
    return_cost = buy_price * return_rate * 0.5
    margin_after_returns = net_margin - return_cost
    net_margin_pct_adj = margin_after_returns / sell_price if sell_price > 0 else 0
    buffered = net_margin_pct_adj * (1 - MARGIN_BUFFER_PCT)
    sw = _seller_weight(seller_count)
    ups = estimated_monthly_units / max(seller_count, 1)
    stf = 1.0 / max(days_to_sell_through, 1)
    pvs = ups * buffered * stf * sw
    if net_margin_pct_adj < 0.10: tier, signal = "T3", "SKIP"
    elif pvs >= 0.8:               tier, signal = "T1", "BUY"
    elif pvs >= 0.4:               tier, signal = "T2", "PAPER TRADE"
    else:                          tier, signal = "T3", "SKIP"
    return {"tier": tier, "signal": signal, "pvs_score": round(pvs, 6),
            "net_margin": round(net_margin, 2), "net_margin_pct": round(net_margin_pct_adj, 4)}

# ===========================================================================
# Tests
# ===========================================================================

print("\n--- FBA Fee Calculator ---")
check("4oz item = $3.06", get_fba_fee(4) == 3.06)
check("12oz item = $3.24", get_fba_fee(12) == 3.24)
check("16oz item = $3.33", get_fba_fee(16) == 3.33)
check("32oz (2lb) = $3.56", get_fba_fee(32) == 3.56)
check("Large bulky 32oz = $9.61 base", round(get_fba_fee(32, "large_bulky"), 2) == 9.61)
check("Large bulky 48oz (3lb) = $9.99", round(get_fba_fee(48, "large_bulky"), 2) == 9.99)

print("\n--- Brand Compliance Checker ---")
check("Nike = IP_RISKY", check_brand("Nike")["status"] == "IP_RISKY")
check("Apple = IP_RISKY + GATED", check_brand("Apple")["status"] == "IP_RISKY" and check_brand("Apple")["is_gated"])
check("Sony = GATED (not IP_RISKY)", check_brand("Sony")["status"] == "GATED")
check("Yeti = IP_RISKY", check_brand("Yeti")["status"] == "IP_RISKY")
check("Zesty Paws = CLEAR", check_brand("Zesty Paws")["status"] == "CLEAR")
check("Greenies = CLEAR", check_brand("Greenies")["status"] == "CLEAR")
check("Case insensitive: NIKE = IP_RISKY", check_brand("NIKE")["status"] == "IP_RISKY")

print("\n--- SKU Scorer ---")

# Strong buy: low cost, good margin, few sellers, high velocity (200 units/month)
r = score_sku(buy_price=14.20, sell_price=28.99, weight_oz=20,
              category="Pet Supplies", seller_count=3,
              estimated_monthly_units=200, days_to_sell_through=14)
print(f"  Greenies test: {r['tier']} / {r['signal']} / PVS={r['pvs_score']} / margin={r['net_margin_pct']:.1%}")
check("Good product scores T1 or T2", r["tier"] in ("T1", "T2"))
check("Positive net margin", r["net_margin"] > 0)

# Bad product: thin margins, lots of sellers
r2 = score_sku(buy_price=18.00, sell_price=20.00, weight_oz=16,
               category="Home & Kitchen", seller_count=15,
               estimated_monthly_units=20, days_to_sell_through=120)
print(f"  Bad product test: {r2['tier']} / {r2['signal']} / PVS={r2['pvs_score']} / margin={r2['net_margin_pct']:.1%}")
check("Bad product scores T3", r2["tier"] == "T3")
check("Bad product signal = SKIP", r2["signal"] == "SKIP")

# Margin check: sell below cost should be T3
r3 = score_sku(buy_price=25.00, sell_price=20.00, weight_oz=16, category="Electronics")
check("Negative margin = T3", r3["tier"] == "T3")

# ===========================================================================
# Summary
# ===========================================================================

print(f"\n{'='*40}")
print(f"  {PASS} passed  |  {FAIL} failed")
print(f"{'='*40}\n")
sys.exit(0 if FAIL == 0 else 1)
